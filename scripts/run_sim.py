from generate_group_orders import generate_final_group_orders
from allocate_ordering_times import allocate_ordering_times
from google.cloud import bigquery

import os
import pandas as pd
import uuid
import datetime
import csv

def prepare_order_data(group_orders):
    """
    Processes group_orders and returns a list of dicts with keys:
    table_no, item_uuid, datetime_ordered, dep, order_uuid
    """
    department_by_category = {
        "starters": "kitchen", "mains": "kitchen",
        "desserts": "kitchen", "sides": "kitchen",
        "alc_drinks": "bar", "non_alc_drinks": "bar",
        "wines": "bar", "dessert_wines": "bar"
    }

    order_ids = {}
    rows = []

    for group_key, group_data in group_orders.items():
        table_no = group_data.get("table_no", "")
        for category, dep in department_by_category.items():
            items = group_data.get(category, [])
            for item in items:
                if item is None:
                    continue
                item_uuid, order_time = item if isinstance(item, tuple) else (item, None)
                order_time_str = order_time.isoformat() if order_time else None
                order_key = (table_no, order_time_str, dep)

                if order_key not in order_ids:
                    order_ids[order_key] = str(uuid.uuid4())

                rows.append({
                    "table_no": table_no,
                    "item_uuid": item_uuid,
                    "datetime_ordered": order_time_str,
                    "dep": dep,
                    "order_uuid": order_ids[order_key]
                })

    return rows

def save_orders_summary_csv(group_orders):
    orders = prepare_order_data(group_orders)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    filename = f"orders_for_night_{today_str}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["table_no", "item_uuid", "datetime_ordered", "dep", "order_uuid"])
        writer.writeheader()
        writer.writerows(orders)

    print(f"CSV summary saved as {filename}")

def save_orders_to_bigquery(group_orders):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "annular-mesh-453913-r6-98bf2733520c.json"
    client = bigquery.Client()

    table_ref = client.dataset("restaurant_data").table("orders")
    rows_to_insert = prepare_order_data(group_orders)

    errors = client.insert_rows_json(table_ref, rows_to_insert)
    if errors:
        print(f"BigQuery Insert Errors: {errors}")
    else:
        print("Data successfully inserted into BigQuery!")

if __name__ == "__main__":
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../credentials/annular-mesh-453913-r6-98bf2733520c.json"
    client = bigquery.Client()

    try:
        ala_carte_data = client.query("SELECT * FROM `restaurant_data.a_la_carte_menu`").to_dataframe()
        desserts_data = client.query("SELECT * FROM `restaurant_data.dessert_menu`").to_dataframe()
        drinks_data  = client.query("SELECT * FROM `restaurant_data.cocktails_and_beer_menu`").to_dataframe()
        wine_data    = client.query("SELECT * FROM `restaurant_data.wine_menu`").to_dataframe()
    except Exception as e:
        print(f"Error occurred while fetching data from BigQuery: {e}")
        raise

    ala_carte_df = pd.DataFrame(ala_carte_data)
    desserts_df = pd.DataFrame(desserts_data)
    drinks_df = pd.DataFrame(drinks_data)
    wine_df = pd.DataFrame(wine_data)

    master_df = pd.concat([ala_carte_df, desserts_df, drinks_df, wine_df], ignore_index=True)
    master_df.to_csv("master_df_export.csv", index=False)

    group_orders = generate_final_group_orders(master_df)
    group_orders = allocate_ordering_times(group_orders)

    #save_orders_summary_csv(group_orders)
    save_orders_to_bigquery(group_orders)
