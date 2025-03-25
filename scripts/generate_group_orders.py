import random
import json
import datetime
import os


file_counter = 1 # used to name file logs
verbose = False # turn to true if you want to see what the structures look like
config_file = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim_config.json"))



def generate_customer_order_intention():
    """
    Generates a random order intention based on probabilities loaded from a config file.

    Returns:
        dict: A dictionary representing what a single customer would order during the course of the night.
    """
    # Load the order configuration from the JSON file
    with open(config_file, "r") as f:
        probabilities = json.load(f)

    customer_order_intention_dict = {
        "n_alc_drinks":             sum(int(random.random() < p) for p in probabilities["n_alc_drinks"]),
        "n_wine_servings":          sum(int(random.random() < p) for p in probabilities["n_wine_servings"]),          # Determines how many 250ml servings the customer will have
        "n_dessert_wine_servings":  sum(int(random.random() < p) for p in probabilities["n_dessert_wine_servings"]),  # Determines how many 70ml servings the customer will have
        "n_non_alc_drinks":         sum(int(random.random() < p) for p in probabilities["n_non_alc_drinks"]),
        "b_starter":                bool(random.random() < probabilities["b_starter"][0]),
        "b_main":                   bool(random.random() < probabilities["b_main"][0]),
        "b_dessert":                bool(random.random() < probabilities["b_dessert"][0])
    }

    return customer_order_intention_dict

def generate_list_of_intentions():
    """
    Generates a list of customer order intentions based on the day of the week.
    
    Returns:
        list: A list of order intention dictionaries.
    """
    # Load the order configuration from the JSON file
    with open(config_file, "r") as f:
        probabilities = json.load(f)
    
    # Get the min and max number of customers depending on the day of the week set in the config file
    today_weekday = datetime.datetime.today().weekday()
    min_customers, max_customers = probabilities["customer_count_range"][str(today_weekday)]
    
    order_count = random.randint(min_customers, max_customers)
    
    all_customer_orderintentions = [generate_customer_order_intention() for _ in range(order_count)]
    
    log_generation_step(all_customer_orderintentions, "list_of_intentions")
    return all_customer_orderintentions

def generate_customer_order(customer_order_intention_dict, full_menu_df):
    """
    Processes a customer order intention (in the form of an order dictionary) 
    and returns a new structured dictionary with UUIDs of items
    from the menu and wine serving counts (to be processed later on).

    Parameters:
        order_dict (dict): The dictionary containing order details.
        full_menu_df (pd.DataFrame): The master dataframe containing menu items.

    Returns:
        dict: A structured dictionary with ordered items and serving counts.
    """
    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)
    
    customer_order_dict = {
        "alc_drinks": [],                                                  # List of alcoholic drink UUIDs
        "n_wine_servings": customer_order_intention_dict["n_wine_servings"],                  # Total wine servings, to be processed later
        "n_dessert_wine_servings": customer_order_intention_dict["n_dessert_wine_servings"],  # Total dessert wine servings, to be processed later
        "non_alc_drinks": [],                                              # List of non-alcoholic drink UUIDs
        "starter_id": None,                                                # Starter UUID
        "main_id": None,                                                   # Main UUID
        "dessert_id": None                                                 # Dessert UUID
    }

    # Select alcoholic drinks
    if customer_order_intention_dict["n_alc_drinks"] > 0:
        alc_categories = config["categories"]["alc_drinks"]
        alc_options = full_menu_df[full_menu_df["category"].isin(alc_categories)]
        customer_order_dict["alc_drinks"] = alc_options.sample(n=min(customer_order_intention_dict["n_alc_drinks"], len(alc_options)))["item_uuid"].tolist()

    # Select non-alcoholic drinks
    if customer_order_intention_dict["n_non_alc_drinks"] > 0:
        non_alc_categories = config["categories"]["non_alc_drinks"]
        non_alc_options = full_menu_df[full_menu_df["category"].isin(non_alc_categories)]
        customer_order_dict["non_alc_drinks"] = non_alc_options.sample(n=min(customer_order_intention_dict["n_non_alc_drinks"], len(non_alc_options)))["item_uuid"].tolist()

    # Select a starter
    if customer_order_intention_dict["b_starter"]:
        starter_categories = config["categories"]["starters"]
        starter_options = full_menu_df[full_menu_df["category"].isin(starter_categories)]
        if not starter_options.empty:
            customer_order_dict["starter_id"] = starter_options.sample(n=1)["item_uuid"].values[0]

    # Select a main course
    if customer_order_intention_dict["b_main"]:
        main_categories = config["categories"]["mains"]
        main_options = full_menu_df[full_menu_df["category"].isin(main_categories)]
        if not main_options.empty:
            customer_order_dict["main_id"] = main_options.sample(n=1)["item_uuid"].values[0]

    # Select a dessert
    if customer_order_intention_dict["b_dessert"]:
        dessert_categories = config["categories"]["desserts"]
        dessert_options = full_menu_df[full_menu_df["category"].isin(dessert_categories)]
        if not dessert_options.empty:
            customer_order_dict["dessert_id"] = dessert_options.sample(n=1)["item_uuid"].values[0]

    # WINE TO BE PROCESSED NEXT AS A SHARED ITEM WITHIN A GROUP
    
    return customer_order_dict

def group_customer_orders(all_customer_orders, full_menu_df):
    """
    Groups processed customer orders into parties based on two criteria:
      1. Customers without starters are grouped into parties of 1 to 4.
      2. Customers with the same sharing main item (if its category is "Large Cuts") are grouped into parties of 2 to 6.
      3. The remaining customers are grouped into parties of 1 to 4.
      
    Returns:
        dict: A dictionary mapping group_id to a list of customer order indices.
    """
    
    group_mapping = {}
    assigned = set()
    group_id = 1

    # Grouping 1: Customers without starters
    non_starter_orders = [idx for idx, order in all_customer_orders if order["starter_id"] is None]
    i = 0
    while i < len(non_starter_orders):
        group_size = random.randint(1, 4)
        group_size = min(group_size, len(non_starter_orders) - i)
        group_members = non_starter_orders[i:i+group_size]
        group_mapping[group_id] = group_members
        assigned.update(group_members)
        group_id += 1
        i += group_size

    # Grouping 2: Customers with the same main item in "Large Cuts"
    large_cuts_groups = {}
    for idx, order in all_customer_orders:
        if idx in assigned:
            continue
        main_id = order["main_id"]
        if main_id is not None:
            main_cat_series = full_menu_df.loc[full_menu_df["item_uuid"] == main_id, "category"]
            if not main_cat_series.empty and main_cat_series.values[0] == "Large Cuts":
                large_cuts_groups.setdefault(main_id, []).append(idx)
    for main_id, order_list in large_cuts_groups.items():
        if len(order_list) >= 2:
            # Split into chunks of at most 6; merge last chunk if it has fewer than 2 members
            chunks = [order_list[i:i+6] for i in range(0, len(order_list), 6)]
            if len(chunks) > 1 and len(chunks[-1]) < 2:
                if len(chunks[-2]) + len(chunks[-1]) <= 6:
                    chunks[-2].extend(chunks[-1])
                    chunks.pop()
            for chunk in chunks:
                if len(chunk) >= 2:
                    group_mapping[group_id] = chunk
                    assigned.update(chunk)
                    group_id += 1

    # Group remaining customers randomly in groups of 1 to 4
    remaining = [idx for idx, order in all_customer_orders if idx not in assigned]
    random.shuffle(remaining)
    i = 0
    while i < len(remaining):
        group_size = random.randint(1, 4)
        group_size = min(group_size, len(remaining) - i)
        group_members = remaining[i:i+group_size]
        group_mapping[group_id] = group_members
        assigned.update(group_members)
        group_id += 1
        i += group_size

    log_generation_step(group_mapping, "group_mapping")
    return group_mapping

def select_wine_from_menu(required_ml, wine_categories, full_menu_df):
    """
    Selects wine items from the provided categories in full_menu_df to meet the required volume.
    
    Parameters:
        required_ml (int): The total required wine volume in milliliters.
        wine_categories (list): List of wine categories to filter by.
        full_menu_df (DataFrame): The full menu dataframe.
    
    Returns:
        list: A list of wine orders (item_uuid, item_name, serving_size).
    """
    wine_order_list = []

    # Loop until we meet the required volume
    while required_ml > 0:
        # Select a random wine from the available categories
        candidates = full_menu_df[full_menu_df["category"].isin(wine_categories)]
        
        if candidates.empty:
            raise ValueError("No wines found in the specified categories.")
        
        # Randomly sample one wine item from the selected candidates
        chosen = candidates.sample(n=1).iloc[0]
        
        # Add the selected wine's UUID to the wine order list
        wine_order_list.append(chosen["item_uuid"])

        # Decrease the required volume by the selected wine's serving size
        required_ml -= chosen["serving_size"]

    return wine_order_list

def generate_group_wine_orders(customer_groups, all_customer_orders, full_menu_df):
    """
    For each group, aggregates required wine ml based on the number of servings ordered
    and selects wine items from full_menu_df until the requirement is met.
    
    Returns:
        dict: Mapping of group_id to a dictionary containing lists of wine orders and dessert wine orders.
              Each order tuple is (item_uuid, item_name, serving_size).
    """
    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)
    
    # Get wine categories from the config file
    wine_categories = config["categories"]["wine"]
    dessert_wine_categories = config["categories"]["dessert_wine"]
    
    # Initialize an empty dictionary to store the wine orders for each group
    group_wine_orders = {}

    # Loop through each group to generate the wine orders
    for group_id, indices in customer_groups.items():
        
        # Calculate the total number of regular wine and dessert wine servings for the group
        total_wine_servings = sum(all_customer_orders[i][1]["n_wine_servings"] for i in indices)
        total_dessert_wine_servings = sum(all_customer_orders[i][1]["n_dessert_wine_servings"] for i in indices)
        
        # Calculate the required wine and dessert wine volume (in milliliters)
        required_wine_ml = total_wine_servings * config["wine_serving_sizes"]["wine_serving"]  # 250ml per wine serving
        required_dessert_wine_ml = total_dessert_wine_servings * config["wine_serving_sizes"]["dessert_wine_serving"]  # 70ml per dessert wine serving

        # Select regular wines
        wine_order_list = select_wine_from_menu(required_wine_ml, wine_categories, full_menu_df)
        
        # Select dessert wines
        dessert_wine_order_list = select_wine_from_menu(required_dessert_wine_ml, dessert_wine_categories, full_menu_df)

        # Store the wine and dessert wine orders for the group
        group_wine_orders[group_id] = {
            "wine_orders": wine_order_list,
            "dessert_wine_orders": dessert_wine_order_list
        }
    
    log_generation_step(group_wine_orders, "group_wine_orders")
    return group_wine_orders

def generate_group_side_orders(customer_groups, all_customer_orders, full_menu_df):
    """
    For each group, generates side orders for each customer.
    Each customer gets one random item from category "Sides".
    If the customer's main item is in "Large Cuts" or "Steaks",
    they also get a random item from "Sauces" and some random chance for
    an item from "extras".
    
    Returns:
        dict: Mapping of group_id to a dictionary mapping customer index to their side orders,
              where each side order is a dict with keys "side", "sauce", and "extras" (all are UUID's).
    """
    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)
    
    # Get the side, sauce, and extras categories from the config file
    side_categories = config["categories"]["sides"]
    sauce_categories = config["categories"]["sauces"]
    extras_categories = config["categories"]["extras"]
    
    group_side_orders = {}
    for group_id, indices in customer_groups.items():
        side_orders = {}
        for idx in indices:
            order = all_customer_orders[idx][1]
            
            # Random side from category "Sides"
            side_candidates = full_menu_df[full_menu_df["category"].isin(side_categories)]
            if not side_candidates.empty:
                side_item = side_candidates.sample(n=1).iloc[0]["item_uuid"]
            else:
                side_item = None

            sauce_item = None
            extras_item = None
            
            # If main item is from "Large Cuts" or "Steaks", add sauce and possibly extras
            if order["main_id"] is not None:
                main_cat_series = full_menu_df.loc[full_menu_df["item_uuid"] == order["main_id"], "category"]
                if not main_cat_series.empty and main_cat_series.values[0] in ["Large Cuts", "Steaks"]:
                    # Select a sauce
                    sauce_candidates = full_menu_df[full_menu_df["category"].isin(sauce_categories)]
                    if not sauce_candidates.empty:
                        sauce_item = sauce_candidates.sample(n=1).iloc[0]["item_uuid"]
                    
                    # Chance for extras from config
                    if random.random() < random.uniform(
                                                    config["chance_of_ordering_an_extra"]["min_chance"], 
                                                    config["chance_of_ordering_an_extra"]["max_chance"]):
                        extras_candidates = full_menu_df[full_menu_df["category"].isin(extras_categories)]
                        if not extras_candidates.empty:
                            extras_item = extras_candidates.sample(n=1).iloc[0]["item_uuid"]
            
            side_orders[idx] = {"side": side_item, "sauce": sauce_item, "extras": extras_item}
        group_side_orders[group_id] = side_orders
    
    log_generation_step(group_side_orders, "group_side_orders")
    return group_side_orders

def generate_final_group_orders(full_menu_df, verboseMode=False):
    """
    Processes all orders, groups them, and builds a nested dictionary of group orders.
    Then, it prints a human-readable summary to "group_orders.txt" and returns the nested dictionary.
    
    The returned dictionary has the following format:
    
      {
         "group_1": {
              "starters": [uuid, uuid, ...],
              "mains": [uuid, uuid, ...],
              "desserts": [uuid, ...],
              "alc_drinks": [uuid, uuid, ...],
              "non_alc_drinks": [uuid, ...],
              "sides": [uuid, uuid, ...],
              "wines": [uuid, ...],
              "dessert_wines": [uuid, ...]
         },
         "group_2": { ... },
         ...
      }

    """
    global verbose
    if verboseMode: 
        verbose = True
    
    
    all_order_intentions = generate_list_of_intentions()

    # Generate individual customer orders and add them to a list
    all_customer_orders = []
    for i, order_intention_dict in enumerate(all_order_intentions):
        customer_order = generate_customer_order(order_intention_dict, full_menu_df)
        all_customer_orders.append((i, customer_order))           

    # Group customers into parties based on a few critera, see group_customer_orders(...)
    customer_groups = group_customer_orders(all_customer_orders, full_menu_df)
    
    # Generate group wine orders and side orders 
    group_wine_orders = generate_group_wine_orders(customer_groups, all_customer_orders, full_menu_df)
    group_side_orders = generate_group_side_orders(customer_groups, all_customer_orders, full_menu_df)
    
    # Build nested dictionary structure: keys are "group_X"
    final_group_orders = {}
    for group_id, customers in customer_groups.items():
        group_key = f"group_{group_id}"
        final_group_orders[group_key] = {
            "starters": [],
            "mains": [],
            "desserts": [],
            "alc_drinks": [],
            "non_alc_drinks": [],
            "sides": [],
            "wines": [],
            "dessert_wines": []
        }
        # for every customer in a group extract the id of their starter, main, dessert and alc and non-alc drinks
        # and add it to the relevant group list
        for customer in customers:
            customer_order = all_customer_orders[customer][1]
            final_group_orders[group_key]["starters"].append(
                customer_order["starter_id"] if customer_order["starter_id"] is not None else None)
            final_group_orders[group_key]["mains"].append(
                customer_order["main_id"] if customer_order["main_id"] is not None else None)
            final_group_orders[group_key]["desserts"].append(
                customer_order["dessert_id"] if customer_order["dessert_id"] is not None else None)
            
            if customer_order["alc_drinks"]:
                final_group_orders[group_key]["alc_drinks"].extend(
                    customer_order["alc_drinks"])
            if customer_order["non_alc_drinks"]:
                final_group_orders[group_key]["non_alc_drinks"].extend(
                    customer_order["non_alc_drinks"])
        
        # Sides: aggregate each customer's side, sauce, extras from group_side_orders
        for customer in customers:
            side_order = group_side_orders.get(group_id, {}).get(customer, {})
            if side_order.get("side"):
                final_group_orders[group_key]["sides"].append(side_order.get("side"))
            if side_order.get("sauce"):
                final_group_orders[group_key]["sides"].append(side_order.get("sauce"))
            if side_order.get("extras"):
                final_group_orders[group_key]["sides"].append(side_order.get("extras"))

        # Wines: use the wine orders from group_wine_orders; we want the UUID (first element of the tuple)
        wines = group_wine_orders.get(group_id, {}).get("wine_orders", [])
        dessert_wines = group_wine_orders.get(group_id, {}).get("dessert_wine_orders", [])
        
        final_group_orders[group_key]["wines"] = [w for w in wines]
        final_group_orders[group_key]["dessert_wines"] = [w for w in dessert_wines]

    log_generation_step(final_group_orders, "final_group_orders")
    return final_group_orders

def log_generation_step(data, filename_prefix="output"):
    """Deletes the content of the file if it exists, and writes the new data to the 'data/raw/sim_logs' directory only if verbose is True."""
    global verbose, file_counter

    # If verbose is False, skip logging
    if not verbose:
        return

    # Get the directory where the script is located and move up one directory
    base_dir = os.path.dirname(__file__)  # Get the path of the current script
    logs_directory = os.path.join(base_dir, "..", "data", "raw", "sim_logs")  # Path to the data/raw/sim_logs folder

    # Ensure the directory exists
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)

    # Get the file name with the number at the front and zero-padded number
    filename = f"{file_counter:02d}_{filename_prefix}.txt"
    file_path = os.path.join(logs_directory, filename)

    # Write new data
    with open(file_path, "w") as f:
        f.write(f"{json.dumps(data, indent=4)}\n\n")

    # Increment the counter after each file generation
    file_counter += 1
