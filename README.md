# Restaurant Service Simulation

A simple simulation of a restaurant's order-taking process that generates structured data for analytics and backend processing. It supports exporting data to both CSV and Google BigQuery.


The simulation:
- Pulls real-time menu data from BigQuery
- Simulates customer group orders with timestamps
- Allocates ordering times to items
- Outputs data to:
  - CSV file for local records
  - Google BigQuery for scalable analytics 

<br>


## 📂 Project Structure

```bash
restaurant_service_simulation/
├── requirements.txt                  # Project dependencies
├── sim_config.json                   # Configuration file for simulation
├── README.md                         # Project documentation

├── credentials/                      # Google Cloud credentials and notes
│   ├── bigquery_key.json             # Service account key for BigQuery
│   └── README.md                     # Explanation of credential usage

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
<br>

## 📚 Navigation

- [📂 Project Structure](#-project-structure)
- [⚙️ Requirements](#️-requirements)
- [🔐 Set Up Google Credentials](#-set-up-google-credentials)
- [▶️ How to Run](#️-how-to-run)
- [🧠 Notes](#-notes)
- [📄 License](#-license)


<br>



## ⚙️ Requirements
- Python 3.9+
- Google Cloud SDK / Service Account Key
- BigQuery tables:
  - `restaurant_data.a_la_carte_menu`
  - `restaurant_data.dessert_menu`
  - `restaurant_data.cocktails_and_beer_menu`
  - `restaurant_data.wine_menu`



<br>

## 🔐 Set Up Google Credentials
Create a service account in GCP with access to BigQuery, download the JSON key, and set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account.json"
```
Or on Windows PowerShell:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\your-service-account.json"
```

<br>

## ▶️ How to Run
For a deeper understanding of how the simulation works under the hood, see:

- [🧾 generate_group_orders.md](doc/generate_group_orders.md) – Explains how randomised group orders are generated.
- [⏱️ allocate_ordering_times.md](doc/allocate_ordering_times.md) – Details how timestamps are assigned to each order item.

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

<br>

## 🧠 Notes
- The simulation logic is fully customisable through `sim_config.json`: you can adjust how group orders are generated or how ordering times are distributed.
- If your menu tables have different schemas, update the BigQuery queries accordingly.

<br>

## 📄 License
This project is for educational and internal use. Customize as needed for production.
