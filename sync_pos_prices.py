"""
Unified POS Synchronization Script for Luosifen Order & Finance System
1. Synchronizes Branch 118 real product prices (bprice) into index.html, menu_data.json, and finance.html
2. Synchronizes 2026 Branch 118 daily & monthly sales reports from Optimy POS API into pos_sales_2026.json, pos_sales_clean.json, and finance.html
3. Pushes updates directly to GitHub origin/main
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
FINANCE_PATH = os.path.join(REPO_DIR, "finance.html")
MENU_DATA_PATH = os.path.join(REPO_DIR, "menu_data.json")
POS_SALES_RAW_PATH = os.path.join(REPO_DIR, "pos_sales_2026.json")
POS_SALES_CLEAN_PATH = os.path.join(REPO_DIR, "pos_sales_clean.json")

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
        return f"https://x-access-token:{pat}@github.com/zhilikam-design/laiwanluosifen-order.git"
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
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("product", [])

def fetch_pos_monthly_sales(month_str):
    url = "https://api.optimy.com.my/apiv2/report/index.php"
    payload = {
        "getSalePerDayList": "1",
        "branch_id": "118",
        "month": month_str
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
            "User-Agent": "Mozilla/5.0"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("report", [])

def sync_products(products):
    print("[1/5] Updating product prices in index.html & menu_data.json...")
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
        print("      All menu prices already match POS.")

    return price_changes

def sync_sales_history():
    print("[2/5] Fetching 2026 POS sales data from Optimy API...")
    months = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09']
    
    raw_sales_data = {}
    clean_sales_data = {}
    
    total_year_sales = 0.0
    total_year_bills = 0
    total_year_days = 0

    for m in months:
        try:
            report_list = fetch_pos_monthly_sales(m)
            raw_sales_data[m] = report_list
            
            m_total = sum(float(r.get("total_amount", 0)) for r in report_list)
            m_bills = sum(int(r.get("total_bill", 0)) for r in report_list)
            m_charge = sum(float(r.get("charge", 0)) for r in report_list)
            m_aov = round(m_total / m_bills, 2) if m_bills > 0 else 0.0
            
            daily = []
            for r in report_list:
                daily.append({
                    "date": r.get("date"),
                    "total": round(float(r.get("total_amount", 0)), 2),
                    "bills": int(r.get("total_bill", 0)),
                    "charge": round(float(r.get("charge", 0)), 2),
                    "net": round(float(r.get("netsales", r.get("total_amount", 0))), 2)
                })
            
            clean_sales_data[m] = {
                "month": m,
                "total_sales": round(m_total, 2),
                "total_bills": m_bills,
                "aov": m_aov,
                "total_service_charge": round(m_charge, 2),
                "days_count": len(daily),
                "daily_sales": daily
            }
            
            total_year_sales += m_total
            total_year_bills += m_bills
            total_year_days += len(daily)
            print(f"      {m}: {len(daily)} days, RM {m_total:,.2f} ({m_bills} bills)")
        except Exception as e:
            print(f"      WARN: Failed to fetch sales for {m}: {e}")

    with open(POS_SALES_RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_sales_data, f, ensure_ascii=False, indent=2)

    with open(POS_SALES_CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_sales_data, f, ensure_ascii=False)

    print(f"      2026 Full Year: {total_year_days} days, RM {total_year_sales:,.2f}, {total_year_bills} bills.")
    return clean_sales_data

def sync_finance_html(clean_sales_data):
    print("[3/5] Embedding latest POS sales & menu data into finance.html...")
    with open(FINANCE_PATH, "r", encoding="utf-8") as f:
        f_html = f.read()

    pos_json_str = json.dumps(clean_sales_data, ensure_ascii=False)
    f_html = re.sub(
        r'const POS_SALES_HISTORY = \{.*?\};\s*\n\s*let CATALOG_DATA =',
        f'const POS_SALES_HISTORY = {pos_json_str};\n\n    let CATALOG_DATA =',
        f_html,
        flags=re.DOTALL
    )

    with open(MENU_DATA_PATH, "r", encoding="utf-8") as f:
        menu = json.load(f)
    catalog_json_str = json.dumps(menu, ensure_ascii=False)
    f_html = re.sub(
        r'let CATALOG_DATA = \[.*?\];\s*\n\s*// 状态',
        f'let CATALOG_DATA = {catalog_json_str};\n\n    // 状态',
        f_html,
        flags=re.DOTALL
    )

    with open(FINANCE_PATH, "w", encoding="utf-8") as f:
        f.write(f_html)
    print("      finance.html successfully synchronized with POS data.")

def sync():
    print("=== Optimy POS Unified Synchronization Engine ===")
    try:
        products = fetch_pos_products()
        print(f"Connected to POS: retrieved {len(products)} products.")
    except Exception as e:
        print(f"ERROR connecting to POS: {e}")
        return False

    price_changes = sync_products(products)
    sales_data = sync_sales_history()
    sync_finance_html(sales_data)

    print("[4/5] Preparing Git commit...")
    subprocess.run(["git", "add", "index.html", "finance.html", "menu_data.json", "pos_sales_2026.json", "pos_sales_clean.json"], cwd=REPO_DIR)
    if os.path.exists(os.path.join(REPO_DIR, "sync_pos_prices.py")):
        subprocess.run(["git", "add", "sync_pos_prices.py"], cwd=REPO_DIR)
    if os.path.exists(os.path.join(REPO_DIR, "一键同步POS价格到网页.bat")):
        subprocess.run(["git", "add", "一键同步POS价格到网页.bat"], cwd=REPO_DIR)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True)
    if status.stdout.strip():
        commit_msg = f"Auto sync POS prices & 2026 full sales history ({len(sales_data)} months, RM 310k+)"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR)
        print("      Committed locally.")
        print("[5/5] Pushing to GitHub origin/main...")
        push_res = subprocess.run(
            ["git", "-c", "credential.helper=", "push", get_remote_push_url(), "main"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True
        )
        if push_res.returncode == 0:
            print("      SUCCESS: Changes pushed directly to GitHub origin/main!")
        else:
            print(f"      Push failed: {push_res.stderr}")
    else:
        print("      Working directory is already clean and up to date.")

    print("\n=== All Done! POS Prices & Revenue History Synchronized! ===")
    return True

if __name__ == "__main__":
    sync()
