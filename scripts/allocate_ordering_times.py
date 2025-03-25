
import random
import datetime
import json
import os

config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim_config.json")


def allocate_booking_times(group_orders):
    """
    Allocates booking start times for each group in group_orders.
    
    Rules (from config):
      - 1-2 guests: 90 minutes; candidate tables: 2-seat list.
      - 3-4 guests: 150 minutes; candidate tables: 4-seat list.
      - 5+ guests: 180 minutes; candidate tables: 6-seat list.
    
    Bookings can start every 15 minutes between 5:00 PM and 9:00 PM.
    The ideal start time is 8:00 PM; if that time is unavailable on a candidate table,
    the function searches for alternative start times (e.g. 7:45, 8:15, 7:30, etc.)
    until a free slot is found. It also reassigns the table if needed.
    
    The function returns the updated group_orders with two new keys added to each group:
        "booking_time": a datetime object for the start time,
        "booking_duration": a timedelta for the booking length.
    """

    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)

    # Fetch lists of table numbers from config 
    tables_2_top = config["two_top_tables"]
    tables_4_top = config["four_top_tables"]
    tables_6_top = config["six_top_tables"]
    
    # Build a schedule dictionary for each table (key: table number, value: list of bookings)
    # Each booking is a tuple: (start_time, end_time, group_key)
    table_schedule = {}
    
    # Generate potential start times
    # every 15 minutes between config["opening_time"] and config["last_booking"]
    potential_starts = []
    today = datetime.date.today()
    current = datetime.datetime.combine(today, datetime.time(config["opening_time"], 0))
    service_end = datetime.datetime.combine(today, datetime.time(config["last_booking"], 0))
    while current <= service_end:
        potential_starts.append(current)
        current += datetime.timedelta(minutes=15)
    
    # We want times closest to config["opening_time"] first.
    ideal = datetime.datetime.combine(today, datetime.time(config["opening_time"], 0))
    potential_starts.sort(key=lambda t: abs((t - ideal).total_seconds()))
    
    # For each group, determine duration and candidate tables based on guest count.
    for group_key, group_data in group_orders.items():
        
        guest_count = len(group_data["mains"])  # Each guest orders a main.
        if guest_count <= 2:
            duration = datetime.timedelta(minutes=config["turn_time_two_top"])
            candidate_tables = tables_2_top
        elif guest_count <= 4:
            duration = datetime.timedelta(minutes=config["turn_time_four_top"])
            candidate_tables = tables_4_top
        else:
            duration = datetime.timedelta(minutes=config["turn_time_six_top"])
            candidate_tables = tables_6_top

        allocated = False
        # Try candidate tables in random order.
        candidate_tables_order = candidate_tables[:]
        random.shuffle(candidate_tables_order)
        for table in candidate_tables_order:
            # Initialize table schedule if not yet done.
            if table not in table_schedule:
                table_schedule[table] = []
            # Try each potential start time.
            for start in potential_starts:
                end = start + duration
                # Check for overlap with existing bookings on this table.
                conflict = False
                for booking in table_schedule[table]:
                    existing_start, existing_end, _ = booking
                    # Overlap exists if the intervals intersect.
                    if not (end <= existing_start or start >= existing_end):
                        conflict = True
                        break
                if not conflict:
                    # Booking fits on this table at this start time.
                    group_data["booking_time"] = start
                    group_data["booking_duration"] = duration
                    group_data["table_no"] = table  # Update the table if needed.
                    table_schedule[table].append((start, end, group_key))
                    allocated = True
                    break
            if allocated:
                break
        if not allocated:
            # If no slot was found, set booking time and duration to None.
            group_data["booking_time"] = None
            group_data["booking_duration"] = None
    return group_orders

def allocate_drink_order_times(group_orders):
    """
    For each group in group_orders, update the lists for "alc_drinks" and "non_alc_drinks"
    so that each drink UUID is paired with an ordering timestamp.
    
    Rules:
      - Drinks can only be ordered after the first config["initial_drinks_order_wait_time"] minutes of the booking.
      - Drinks are ordered in rounds.
      - For each drink type:
            * Determine total drinks.
            * Set number of rounds = min(total drinks, number of guests) (each guest is counted by the length of "mains").
            * Partition the total number randomly into that many rounds (each round gets at least one drink).
            * The first round’s timestamp is set to booking_time plus a random time between 
                config["initial_drinks_order_wait_time_min"] and config["initial_drinks_order_wait_time_max"] minutes.
            * Each subsequent round’s timestamp = previous round timestamp + 10 minutes (to make) + a random consumption time (15-25 minutes).
      - Replace the original list (e.g. ['uuid1', 'uuid2', ...]) with a list of tuples:
            [(uuid, order_timestamp), ...]
    """
    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)

    for group_key, group_data in group_orders.items():
        
        booking_time = group_data.get("booking_time")
        if not booking_time:
            continue  # skip if no booking time is set
        # Use the number of mains as the guest count (each guest orders a main).
        guest_count = len(group_data.get("mains", []))
        # Process both drink types.
        for drink_type in ["alc_drinks", "non_alc_drinks"]:
            drink_list = group_data.get(drink_type, [])
            total_drinks = len(drink_list)
            if total_drinks == 0:
                continue
            # Determine number of rounds: if there are at least as many drinks as guests, use guest_count rounds;
            # otherwise, use total_drinks rounds.
            rounds = guest_count if total_drinks >= guest_count else total_drinks
            
            # Partition total_drinks into 'rounds' parts (each at least 1).
            if rounds == 1:
                partition = [total_drinks]
            else:
                # Create a random partition by choosing (rounds - 1) divider points between 1 and total_drinks-1.
                dividers = sorted(random.sample(range(1, total_drinks), rounds - 1))
                partition = []
                prev = 0
                for d in dividers:
                    partition.append(d - prev)
                    prev = d
                partition.append(total_drinks - prev)
            
            # Determine ordering timestamps for each round.
            round_times = []
            # Choose a random delay between 10 and 15 minutes for the first round.
            current_time = booking_time + datetime.timedelta(minutes=random.randint(
                config["initial_drinks_order_wait_time_min"],
                config["initial_drinks_order_wait_time_max"])
                )
            for r in range(rounds):
                round_times.append(current_time)
                # Each round takes 10 minutes to make plus a random consumption time between 15 and 25 minutes.
                consumption_time = random.randint(
                    config["drink_consumption_time_min"],
                    config["drink_consumption_time_max"]
                )
                current_time = current_time + datetime.timedelta(minutes=config["drink_round_prod_time"] + consumption_time)
            
            # Now assign each drink in drink_list to a round according to the partition.
            new_drink_list = []
            idx = 0
            for r in range(rounds):
                count = partition[r]
                for i in range(count):
                    new_drink_list.append((drink_list[idx], round_times[r]))
                    idx += 1
            # Update the group data for the drink type.
            group_data[drink_type] = new_drink_list
    return group_orders

def allocate_food_order_times(group_orders):
    """
    For each group in group_orders, assign ordering timestamps to food items (starters, mains, desserts, and sides)
    following these rules:
    
      - A candidate food order start time is chosen randomly between 
        config["initial_food_order_wait_time_min"] and config["initial_food_order_wait_time_max"] minutes after booking,
        but not before 1 minute after the earliest drink order.
      
      - Starters:
          * If any starters are ordered (non-None values), they are ordered at food_start.
          * Their total time (preparation + consumption) T_starters is randomly chosen between 
                 config["starters_consumption_time_min"] and config["starters_consumption_time_max"] minutes.
          * They finish at: starters_finish = food_start + T_starters.
          * If no starters are ordered, then starters_finish is set to food_start.
      
      - Mains (and sides):
          * If starters exist:
                - A target main preparation time T_main is chosen randomly between
                    config["mains_prep_time_min"] and config["mains_prep_time_max"] minutes.
                - Because the mains have been cooking concurrently during the starters’ period,
                  the additional cooking needed is: additional_cooking = max(0, T_main - T_starters).
                - The mains order time is then set to: mains_order_time = starters_finish + additional_cooking.
          * If no starters exist:
                - The mains are ordered immediately at food_start.
                - The mains will be ready only after waiting a full T_main minutes, where T_main is random between 30 and 40.
          * In both cases, after the order is placed, a consumption time T_consume (random between 30 and 40 minutes)
            is added to determine when the mains are consumed.
      
      - Desserts:
          * Desserts are ordered 2 minutes after the mains have been consumed.
    
    For each food category, each non-None item is replaced by a tuple: (uuid, order_time).
    """

     # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)

    for group_key, group_data in group_orders.items():
        
        booking_time = group_data.get("booking_time")
        if not booking_time:
            continue  # Skip groups without a booking time

        # Determine earliest drink order time (if any)
        drink_times = []
        for tup in group_data.get("alc_drinks", []):
            drink_times.append(tup[1])
        for tup in group_data.get("non_alc_drinks", []):
            drink_times.append(tup[1])
        if drink_times:
            earliest_drink = min(drink_times)
        else:
            earliest_drink = booking_time

        # Choose candidate food start time: random between 
        # config["initial_food_order_wait_time_min"] and config["initial_food_order_wait_time_max"] minutes after booking,
        # but ensure it is at least 1 minute after the earliest drink order.
        candidate_offset = random.randint(
            config["initial_food_order_wait_time_min"],
            config["initial_food_order_wait_time_max"]
            )
        candidate_food_start = booking_time + datetime.timedelta(minutes=candidate_offset)
        food_start = max(candidate_food_start, earliest_drink + datetime.timedelta(minutes=1))
        
        # Process starters.
        starters_list = group_data.get("starters", [])
        starters_exist = any(item is not None for item in starters_list)
        new_starters = []
        if starters_exist:
            # Order all non-None starters at food_start.
            for item in starters_list:
                if item is None:
                    new_starters.append(None)
                else:
                    new_starters.append((item, food_start))
            group_data["starters"] = new_starters
            # Choose T_starters (total time for starters) between 
            # config["starters_consumption_time_min"] and config["starters_consumption_time_max"].
            T_starters = random.randint(
                config["starters_consumption_time_min"],
                config["starters_consumption_time_max"]
                )
            starters_finish = food_start + datetime.timedelta(minutes=T_starters)
        else:
            starters_finish = food_start  # No starters; nothing delays mains ordering.

        # Process mains and sides.
        T_main = random.randint(
            config["mains_prep_time_min"],
            config["mains_prep_time_max"]
            )
        if starters_exist:
            # Mains have been cooking concurrently during the starters.
            additional_cooking = max(0, T_main - (starters_finish - food_start).seconds // 60)
            mains_order_time = starters_finish + datetime.timedelta(minutes=additional_cooking)
        else:
            # If no starters, mains are ordered immediately at food_start.
            mains_order_time = food_start
        # When mains are ordered at food_start (no starters), they are only ready after T_main minutes.
        mains_ready = mains_order_time if starters_exist else (food_start + datetime.timedelta(minutes=T_main))
        T_consume = random.randint(
            config["mains_consumption_time_min"],
            config["mains_consumption__time_max"]
            )
        mains_consumed = mains_ready + datetime.timedelta(minutes=T_consume)
        
        # Update mains and sides: record order time as determined.
        new_mains = [(item, mains_order_time) for item in group_data.get("mains", [])]
        group_data["mains"] = new_mains
        new_sides = [(item, mains_order_time) for item in group_data.get("sides", [])]
        group_data["sides"] = new_sides

        # Process desserts: order a random time between
        # config["desserts_order_time_min"] and config["desserts_order_time_max"] minutes after the mains have been consumed.
        desserts_offset = random.randint(
            config["desserts_order_time_min"],
            config["desserts_order_time_max"]
        )
        desserts_order_time = mains_consumed + datetime.timedelta(minutes=desserts_offset)
        new_desserts = []
        for item in group_data.get("desserts", []):
            if item is None:
                new_desserts.append(None)
            else:
                new_desserts.append((item, desserts_order_time))
        group_data["desserts"] = new_desserts
        
    return group_orders

def allocate_wine_order_times(group_orders):
    """
    For each group in group_orders, update both "wines" and "dessert_wines" as follows:
    
    Regular Wines:
      - Lower bound: earliest drink order time from alc_drinks/non_alc_drinks (or booking_time if none).
      - Upper bound: if any non-None dessert exists, the minimum dessert order time; otherwise, the group’s close time.
      - A random timestamp is chosen between these bounds.
      - If the chosen timestamp is within config["merge_orders_timeframe"] of any other food/drink order time
        (from starters, mains, desserts, alc_drinks, non_alc_drinks), it is adjusted to exactly match that time.
        
    Dessert Wines:
      - Lower bound: if any non-None dessert exists, the minimum dessert order time; otherwise,
                     use the maximum main order time plus config["mains_consumption__time_max"] as an approximation for mains consumption.
      - Upper bound: the group’s close time.
      - A random timestamp is chosen between these bounds and then adjusted (if within timeframe of any candidate time)
        as above.
    
    The function returns the updated group_orders.
    """
    # Load the configuration from the JSON file
    with open(config_file, "r") as f:
        config = json.load(f)

    for group_key, group_data in group_orders.items():
        
        booking_time = group_data.get("booking_time")
        booking_duration = group_data.get("booking_duration")
        if not (booking_time and booking_duration):
            continue
        close_time = booking_time + booking_duration

        # --- Process Regular Wines ---
        # Lower bound: earliest drink order time from alc_drinks/non_alc_drinks or booking_time.
        drink_times = []
        for tup in group_data.get("alc_drinks", []):
            drink_times.append(tup[1])
        for tup in group_data.get("non_alc_drinks", []):
            drink_times.append(tup[1])
        lower_bound = min(drink_times) if drink_times else booking_time

        # Upper bound: if any dessert exists (non-None in desserts), use min(dessert order time); otherwise, close_time.
        dessert_times = []
        for dessert in group_data.get("desserts", []):
            if dessert is not None:
                dessert_times.append(dessert[1])
        if dessert_times:
            upper_bound = min(dessert_times)
        else:
            upper_bound = close_time

        interval_seconds = int((upper_bound - lower_bound).total_seconds())
        new_wines = []
        for wine_uuid in group_data.get("wines", []):
            # If already a tuple (already processed), skip.
            if isinstance(wine_uuid, tuple):
                new_wines.append(wine_uuid)
                continue
            if interval_seconds > 0:
                rand_offset = random.randint(0, interval_seconds)
                order_time = lower_bound + datetime.timedelta(seconds=rand_offset)
            else:
                order_time = lower_bound

            # Gather candidate times from other items.
            candidate_times = []
            for key in ["starters", "mains", "desserts", "alc_drinks", "non_alc_drinks"]:
                for item in group_data.get(key, []):
                    if item is None:
                        continue
                    if isinstance(item, tuple):
                        candidate_times.append(item[1])
            # If within config["merge_orders_timeframe"] seconds of any candidate, adjust to that candidate's time.
            min_diff = None
            closest_time = None
            for candidate in candidate_times:
                diff = abs((order_time - candidate).total_seconds())
                if diff <= config["merge_orders_timeframe"]:
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_time = candidate
            if closest_time is not None:
                order_time = closest_time
            new_wines.append((wine_uuid, order_time))
        group_data["wines"] = new_wines

        # --- Process Dessert Wines ---
        dessert_wine_list = group_data.get("dessert_wines", [])
        new_dessert_wines = []
        # Lower bound: if any dessert exists, use min(dessert order time); otherwise, approximate as (max(mains order time) + 35 min).
        if dessert_times:
            dessert_lower_bound = min(dessert_times)
        else:
            mains_times = []
            for tup in group_data.get("mains", []):
                if isinstance(tup, tuple):
                    mains_times.append(tup[1])
            if mains_times:
                dessert_lower_bound = max(mains_times) + datetime.timedelta(minutes=config["mains_consumption__time_max"])
            else:
                dessert_lower_bound = booking_time

        upper_bound_dw = close_time
        interval_seconds_dw = int((upper_bound_dw - dessert_lower_bound).total_seconds())
        for dw in dessert_wine_list:
            if isinstance(dw, tuple):
                new_dessert_wines.append(dw)
                continue
            if interval_seconds_dw > 0:
                rand_offset = random.randint(0, interval_seconds_dw)
                order_time_dw = dessert_lower_bound + datetime.timedelta(seconds=rand_offset)
            else:
                order_time_dw = dessert_lower_bound

            # Adjust if within 5 minutes of any candidate from other items.
            candidate_times_dw = []
            for key in ["starters", "mains", "desserts", "alc_drinks", "non_alc_drinks"]:
                for item in group_data.get(key, []):
                    if item is None:
                        continue
                    if isinstance(item, tuple):
                        candidate_times_dw.append(item[1])
            min_diff_dw = None
            closest_time_dw = None
            for candidate in candidate_times_dw:
                diff = abs((order_time_dw - candidate).total_seconds())
                if diff <= 300:
                    if min_diff_dw is None or diff < min_diff_dw:
                        min_diff_dw = diff
                        closest_time_dw = candidate
            if closest_time_dw is not None:
                order_time_dw = closest_time_dw
            new_dessert_wines.append((dw, order_time_dw))
        group_data["dessert_wines"] = new_dessert_wines

    
    return group_orders

def allocate_ordering_times(group_orders):
    """
    Calls the other functions in sequence in order to allocate times for booking, drinks, food, and wine.
    
    Args:
        group_orders (dict): The group orders that will be updated with the relevant timestamps.
        
    Returns:
        dict: The updated group_orders with allocated times for booking, drinks, food, and wine.
    """
    # Call each function in order
    group_orders = allocate_booking_times(group_orders)
    group_orders = allocate_drink_order_times(group_orders)
    group_orders = allocate_food_order_times(group_orders)
    group_orders = allocate_wine_order_times(group_orders)

    return group_orders
