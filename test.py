import json
import time
import requests
import pandas as pd
import yaml
from tqdm import tqdm

BASE_URL = "https://censusapi.cbs.gov.np/api/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://censusresults.nsonepal.gov.np",
    "Referer": "https://censusresults.nsonepal.gov.np/"
}

# Mapping of Province IDs to their respective District IDs (1 to 77)
PROVINCE_DISTRICT_MAP = {
    1: list(range(1, 15)),    # Koshi Province (Districts 1 to 14)
    2: list(range(15, 23)),   # Madhesh Province (Districts 15 to 22)
    3: list(range(23, 36)),   # Bagmati Province (Districts 23 to 35)
    4: list(range(36, 47)),   # Gandaki Province (Districts 36 to 46)
    5: list(range(47, 59)),   # Lumbini Province (Districts 47 to 58)
    6: list(range(59, 69)),   # Karnali Province (Districts 59 to 68)
    7: list(range(69, 78))    # Sudurpashchim Province (Districts 69 to 77)
}


def fetch_ward_data(p_id, d_id, m_id):
    """Fetch mapData directly using the confirmed local-level-map endpoint."""
    url = f"{BASE_URL}/local-level-map"
    params = {
        "province": p_id,
        "district": d_id,
        "municipality": m_id,
        "indicator": "population_size"
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if res.status_code == 200:
            payload = res.json()
            if payload.get("success") and "data" in payload and "mapData" in payload["data"]:
                return payload["data"]["mapData"]
    except Exception as e:
        pass
    return None


def run_extraction():
    hierarchical_tree = []
    flattened_rows = []

    print("Starting NSO/CBS Census Data Crawler...")

    for p_id, district_ids in PROVINCE_DISTRICT_MAP.items():
        print(f"\n==========================================")
        print(f"[+] Processing Province {p_id}")
        print(f"==========================================")

        province_node = {
            "province_id": p_id,
            "districts": []
        }

        for d_id in district_ids:
            print(f"  --> Checking District ID: {d_id}")

            district_node = {
                "district_id": d_id,
                "municipalities": []
            }

            # Loop through possible local levels per district (1 to 20 covers all local levels in any district)
            found_any_muni = False
            for m_id in range(1, 21):
                map_data = fetch_ward_data(p_id, d_id, m_id)
                time.sleep(0.05)  # Rate limit prevention

                if map_data:
                    found_any_muni = True
                    gapa_name = map_data[0].get(
                        "gapa_name", f"Local Level {m_id}")

                    muni_node = {
                        "municipality_id": m_id,
                        "municipality_name": gapa_name,
                        "wards": []
                    }

                    print(
                        f"      [✓] Found Municipality {m_id}: {gapa_name} ({len(map_data)} Wards)")

                    for w in map_data:
                        w_no = w.get("ward")
                        total = w.get("total", 0)
                        male = w.get("male", 0)
                        female = w.get("female", 0)
                        households = w.get("household", 0)

                        ward_dict = {
                            "ward_no": w_no,
                            "area_name": w.get("area_name", f"Ward - {w_no}"),
                            "total_population": total,
                            "male_population": male,
                            "female_population": female,
                            "households": households
                        }
                        muni_node["wards"].append(ward_dict)

                        flattened_rows.append({
                            "Province ID": p_id,
                            "District ID": d_id,
                            "Municipality ID": m_id,
                            "Municipality Name": gapa_name,
                            "Ward No": w_no,
                            "Area Name": w.get("area_name", f"Ward - {w_no}"),
                            "Total Households": households,
                            "Total Population": total,
                            "Male Population": male,
                            "Female Population": female
                        })

                    district_node["municipalities"].append(muni_node)

            if found_any_muni:
                province_node["districts"].append(district_node)

        hierarchical_tree.append(province_node)

    # Save outputs
    if flattened_rows:
        print(f"\n[✓] Extracted total {len(flattened_rows)} ward records!")

        # 1. Save JSON
        with open("nepal_census_hierarchy.json", "w", encoding="utf-8") as f:
            json.dump(hierarchical_tree, f, indent=2, ensure_ascii=False)
        print("  --> Saved: nepal_census_hierarchy.json")

        # 2. Save YAML
        with open("nepal_census_hierarchy.yaml", "w", encoding="utf-8") as f:
            yaml.dump(hierarchical_tree, f, allow_unicode=True,
                      default_flow_style=False)
        print("  --> Saved: nepal_census_hierarchy.yaml")

        # 3. Save CSV
        df = pd.DataFrame(flattened_rows)
        df.to_csv("nepal_census_wards.csv", index=False, encoding="utf-8-sig")
        print("  --> Saved: nepal_census_wards.csv")
    else:
        print(
            "\n[!] Failed to extract records. Ensure your internet connection is active.")


if __name__ == "__main__":
    run_extraction()
