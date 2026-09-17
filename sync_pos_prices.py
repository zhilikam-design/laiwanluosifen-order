"""
Automated POS Price Synchronization Script for Luosifen Order System
Fetches live Branch 118 prices (bprice) from Optimy POS API, updates index.html & menu_data.json,
and pushes automatically to GitHub.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import subprocess

REPO_DIR = r"C:\Users\kamhu\.gemini\antigravity\scratch\luosifen-order"
HTML_PATH = os.path.join(REPO_DIR, "index.html")
MENU_DATA_PATH = os.path.join(REPO_DIR, "menu_data.json")

def get_github_pat():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ.get("GITHUB_TOKEN").strip()
    cfg_path = os.path.expanduser(r"~\.gemini\config\mcp_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("mcpServers", {}).get("github", {}).get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip()
        except Exception:
            pass
    return ""

def get_remote_push_url():
    pat = get_github_pat()
    if pat:
        return f"https://x-access-token:{pat}@github.com/zhilikam-design/luosifen-order.git"
    return "origin"

def fetch_pos_products():
    url = "https://api.optimy.com.my/apiv2/product/index.php"
    payload = {
        "getAllProductSpeedUP": "1",
        "company_id": "110",
        "branch_id": "118"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://cp.optimy.com.my",
            "Referer": "https://cp.optimy.com.my/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("product", [])

def sync():
    print("[1/4] Connecting to Optimy POS API...")
    try:
        products = fetch_pos_products()
        print(f"      Successfully fetched {len(products)} products from POS.")
    except Exception as e:
        print(f"      ERROR fetching from POS: {e}")
        return False

    print("[2/4] Reading local menu and comparing prices...")
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    m = re.search(r'let MENU = (\[.*?\]);', html)
    if not m:
        print("      ERROR: Could not find 'let MENU = [...]' in index.html")
        return False
    menu = json.loads(m.group(1))

    price_changes = []

    for item in menu:
        item_id = item["id"].strip()
        pattern = re.compile(rf"^{re.escape(item_id)}(?:\D|$)", re.IGNORECASE)

        match_pos = None
        for p in products:
            p_name = (p.get("name") or "").strip()
            if pattern.match(p_name):
                match_pos = p
                break

        if not match_pos:
            alt_id = item_id
            if item_id.startswith("F0"):
                alt_id = "F" + item_id[2:]
            elif item_id.startswith("F") and len(item_id) == 2 and item_id[1].isdigit():
                alt_id = "F0" + item_id[1]
            alt_pattern = re.compile(rf"^{re.escape(alt_id)}(?:\D|$)", re.IGNORECASE)
            for p in products:
                p_name = (p.get("name") or "").strip()
                if alt_pattern.match(p_name):
                    match_pos = p
                    break

        if not match_pos:
            zh_chars = "".join(re.findall(r'[\u4e00-\u9fa5]', item["name"]))
            for p in products:
                p_name = (p.get("name") or "").strip()
                p_zh = "".join(re.findall(r'[\u4e00-\u9fa5]', p_name))
                if zh_chars and (zh_chars in p_zh or p_zh in zh_chars):
                    match_pos = p
                    break

        if match_pos:
            bprice = match_pos.get("bprice")
            price = match_pos.get("price")
            real_price = None
            if bprice is not None and str(bprice).strip() != "":
                try:
                    real_price = float(bprice)
                except Exception:
                    pass
            if real_price is None and price is not None:
                real_price = float(price)

            if real_price is not None:
                old_p = item["price"]
                if abs(old_p - real_price) > 0.009:
                    price_changes.append({
                        "id": item["id"],
                        "name": item["name"],
                        "old": old_p,
                        "new": real_price
                    })
                item["price"] = real_price

    # Check MODIFIERS
    m_mod = re.search(r'const MODIFIERS = (\{.*?\});\s*\n\s*let cart =', html, flags=re.DOTALL)
    if m_mod:
        mods_data = json.loads(m_mod.group(1))
        addon_groups = mods_data.get("addons", {}).get("groups", [])
        for grp in addon_groups:
            for it in grp.get("items", []):
                it_name = it["name"]
                for p in products:
                    p_name = p.get("name", "")
                    p_sku = p.get("SKU", "")
                    code_match = re.match(r'^([A-Z]\d+)', it_name)
                    if code_match and (code_match.group(1) in p_name or code_match.group(1) == p_sku):
                        bp = p.get("bprice")
                        if bp is not None and str(bp).strip() != "":
                            old_bp = it["price"]
                            new_bp = float(bp)
                            if abs(old_bp - new_bp) > 0.009:
                                price_changes.append({
                                    "id": code_match.group(1),
                                    "name": it_name,
                                    "old": old_bp,
                                    "new": new_bp
                                })
                            it["price"] = new_bp
                            break
        mods_json_str = json.dumps(mods_data, ensure_ascii=False)
        html = re.sub(r'const MODIFIERS = \{.*?\};\s*\n\s*let cart =', f'const MODIFIERS = {mods_json_str};\n\n    let cart =', html, flags=re.DOTALL)

    print("[3/4] Updating local files...")
    menu_json_str = json.dumps(menu, ensure_ascii=False)
    html = re.sub(r'let MENU = \[.*?\];', f'let MENU = {menu_json_str};', html, flags=re.DOTALL)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    with open(MENU_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)

    if price_changes:
        print(f"      Detected {len(price_changes)} price change(s):")
        for c in price_changes:
            print(f"        • {c['id']} {c['name']}: RM {c['old']:.2f} -> RM {c['new']:.2f}")
    else:
        print("      No price differences found (all local prices match Optimy POS).")

    print("[4/4] Synchronizing with GitHub...")
    subprocess.run(["git", "add", "index.html", "menu_data.json"], cwd=REPO_DIR)
    if os.path.exists(os.path.join(REPO_DIR, "sync_pos_prices.py")):
        subprocess.run(["git", "add", "sync_pos_prices.py"], cwd=REPO_DIR)
    if os.path.exists(os.path.join(REPO_DIR, "一键同步POS价格到网页.bat")):
        subprocess.run(["git", "add", "一键同步POS价格到网页.bat"], cwd=REPO_DIR)
    
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if status.stdout.strip():
        commit_msg = f"Auto sync latest prices & tax from Optimy POS ({len(price_changes)} items updated)"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR)
        print("      Changes committed locally.")
        push_res = subprocess.run(
            ["git", "-c", "credential.helper=", "push", get_remote_push_url(), "main"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True
        )
        if push_res.returncode == 0:
            print("      SUCCESS: Pushed directly to GitHub origin/main!")
        else:
            print(f"      Push failed: {push_res.stderr}")
    else:
        print("      Working directory already up to date with remote.")

    print("\n All done! POS synchronization complete.")
    return True

if __name__ == "__main__":
    sync()
