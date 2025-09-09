# Restaurant Order Simulation

A lightweight simulation of a restaurant's order-taking process, designed to generate structured data for analytics and backend workflows. It supports exporting data to both CSV and Google BigQuery.

---

### 🧪 Simulation Overview:

- 📥 Retrieves real-time menu data from **Google BigQuery**
- 👥 Simulates customer group orders with accurate timestamps
- 🍽️ Assigns ordering times to individual items based on department workflows
- 📤 Outputs data to:
  - 📄 **CSV files** for local archival
  - ☁️ **Google BigQuery** for scalable analysis and reporting

⏱️ The simulation is [configured](.github/workflows/daily-run.yml) to run automatically on a daily schedule via **GitHub Actions** ⚙️

## 📂 Project Structure

```bash
restaurant_service_simulation/
├── requirements.txt                  # Project dependencies
├── sim_config.json                   # Configuration file for simulation
├── README.md                         # Project documentation

├── data/
│   └── raw/
│       └── menus/                    # Static CSV copies of menu tables
│           ├── a_la_carte_menu.csv
│           ├── cocktails_and_beer_menu.csv
│           ├── dessert_menu.csv
│           ├── wine_menu.csv
│           └── README.md

├── doc/                              # Internal documentation and diagrams
│   ├── allocate_ordering_times.md
│   ├── generate_group_orders.md
│   ├── order_generation_flowchart.png
│   └── time_allocation_flowchart.png

└── scripts/                          # Core simulation logic
    ├── allocate_ordering_times.py    # Assigns timestamps to simulated orders
    ├── generate_group_orders.py      # Generates randomised group orders
    └── run_sim.py                    # Main script to run the whole simulation
```

## 📚 Navigation

- [📂 Project Structure](#-project-structure)
- [⚙️ BigQuery Set Up](#️-bigquery-set-up)
- [▶️ How to Run](#️-how-to-run)
- [🧠 Notes](#-notes)
- [📄 License](#-license)

## ⚙️ BigQuery Set Up

To run this simulation, you need access to a **BigQuery dataset** called `restaurant_data` containing the following tables:

### 📋 Required Menu Tables:

- `restaurant_data.a_la_carte_menu`
- `restaurant_data.dessert_menu`
- `restaurant_data.cocktails_and_beer_menu`
- `restaurant_data.wine_menu`

### 📝 Output Table:

The simulation will write generated orders to a table called `restaurant_data.orders`.

It must have the following schema:

| field name         | mode     | type      | description                           |
| ------------------ | -------- | --------- | ------------------------------------- |
| `table_no`         | REQUIRED | STRING    | the table that ordered the item       |
| `item_uuid`        | REQUIRED | STRING    | unique ID of the ordered item         |
| `datetime_ordered` | REQUIRED | TIMESTAMP | the time the item was ordered         |
| `dep`              | REQUIRED | STRING    | the department that produced the item |
| `order_uuid`       | REQUIRED | STRING    | unique ID of the order                |

### 🔐 Authentication

Create a **service account** in GCP with access to BigQuery, download the JSON key, and set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"
```

Or on Windows PowerShell:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\your-service-account.json"
```

## ▶️ How to Run

For a deeper understanding of how the simulation works under the hood, see:

- [🧾 generate\_group\_orders.md](doc/generate_group_orders.md) – Explains how randomised group orders are generated.
- [⏱️ allocate\_ordering\_times.md](doc/allocate_ordering_times.md) – Details how timestamps are assigned to each order item.

From the `scripts/` directory:

```bash
python run_sim.py
```

This will:

- Fetch menus from BigQuery
- Generate group orders
- Allocate order times
- Push the data to BigQuery if `save_orders_to_bigquery()`
- (Optional) Export to a CSV file named `orders_for_night_YYYY-MM-DD.csv` if `save_orders_summary_csv()` is uncommented

## 🧠 Notes

- The simulation logic is fully customisable through `sim_config.json`: you can adjust how group orders are generated or how ordering times are distributed.
- If your menu tables have different schemas, update the BigQuery queries accordingly.

## 📄 License

This project is for educational and internal use. Customise as needed for production.



