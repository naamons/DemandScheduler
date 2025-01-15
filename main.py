import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Function to calculate Order Quantity
def calculate_order_quantity(daily_demand, lead_time_days, shipping_time_days, safety_stock_days):
    total_lead_time = lead_time_days + shipping_time_days
    safety_stock = daily_demand * safety_stock_days
    order_quantity = (daily_demand * total_lead_time) + safety_stock
    return order_quantity, total_lead_time, safety_stock

# Function to generate order schedule
def generate_order_schedule(
    start_date, 
    current_inventory, 
    daily_demand, 
    lead_time_days, 
    shipping_time_days, 
    safety_stock_days, 
    product_name, 
    variant_name, 
    variant_sku,
    in_transit_quantity=0,
    expected_arrival=None
):
    total_lead_time = lead_time_days + shipping_time_days
    safety_stock = daily_demand * safety_stock_days
    reorder_point = (daily_demand * total_lead_time) + safety_stock
    order_quantity = (daily_demand * total_lead_time) + safety_stock

    schedule = []
    date = start_date
    end_date = start_date + timedelta(days=365)  # 12 months

    # Adjust current inventory by subtracting in-transit quantity if arrival is in the future
    if in_transit_quantity > 0 and expected_arrival and expected_arrival > start_date:
        available_inventory = current_inventory
        pending_inventory = in_transit_quantity
    else:
        available_inventory = current_inventory + in_transit_quantity
        pending_inventory = 0

    while date < end_date:
        # Calculate days until reorder point is reached
        days_until_reorder = (available_inventory - safety_stock) / daily_demand if daily_demand else float('inf')
        reorder_date = date + timedelta(days=days_until_reorder)

        if reorder_date <= date:
            reorder_date = date

        # Schedule PO placement
        po_date = reorder_date
        arrival_date = po_date + timedelta(days=total_lead_time)

        # Append to schedule
        schedule.append({
            'Product': product_name,
            'Variant': variant_name,
            'SKU': variant_sku,
            'Order Date': po_date.strftime('%Y-%m-%d'),
            'Arrival Date': arrival_date.strftime('%Y-%m-%d'),
            'Order Quantity': order_quantity
        })

        # Update available inventory
        available_inventory += order_quantity
        date = arrival_date  # Move to the arrival date for the next calculation

    return pd.DataFrame(schedule)

# Initialize session state for products and schedules
if 'products' not in st.session_state:
    st.session_state.products = []
if 'schedules' not in st.session_state:
    st.session_state.schedules = {}
if 'selected_product_details' not in st.session_state:
    st.session_state.selected_product_details = None

# Streamlit App
def main():
    st.set_page_config(page_title="Inventory Order Management", layout="wide")
    st.title("📦 Inventory Order Management App")

    st.sidebar.header("🔄 Upload Demand CSV")
    uploaded_file = st.sidebar.file_uploader("Upload your demand CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            demand_df = pd.read_csv(uploaded_file)
            # Validate required columns
            required_columns = {'product_title', 'variant_title', 'variant_sku', 'ending_quantity', 'quantity_sold_per_day'}
            if not required_columns.issubset(demand_df.columns):
                missing = required_columns - set(demand_df.columns)
                st.sidebar.error(f"❌ Missing columns in CSV: {', '.join(missing)}")
                st.stop()
            st.sidebar.success("✅ CSV uploaded successfully!")
            st.write("### 📊 Demand Data")
            st.dataframe(demand_df)
        except Exception as e:
            st.sidebar.error("❌ Error loading CSV file. Please ensure it is a valid CSV.")
            st.stop()
    else:
        st.sidebar.info("🕒 Awaiting CSV file to be uploaded.")
        st.stop()

    st.header("➕ Add Product to Board")

    # Form for Product Selection and Refresh
    with st.form("refresh_form"):
        st.subheader("🔍 Select and Refresh Product Details")
        # Dropdown to select product by name or SKU
        product_options = demand_df.apply(
            lambda row: f"{row['product_title']} - {row['variant_title']} (SKU: {row['variant_sku']})", axis=1
        )
        selected_product = st.selectbox("Select Product", options=product_options)

        refresh = st.form_submit_button("🔄 Refresh Details")

    if refresh:
        try:
            # Extract the selected product's details
            selected_index = product_options.index[demand_df.apply(
                lambda row: f"{row['product_title']} - {row['variant_title']} (SKU: {row['variant_sku']})", axis=1
            ) == selected_product][0]
            selected_row = demand_df.iloc[selected_index]
            st.session_state.selected_product_details = {
                'product_name': selected_row['product_title'],
                'variant_name': selected_row['variant_title'],
                'variant_sku': selected_row['variant_sku'],
                'current_inventory': selected_row['ending_quantity'],
                'daily_demand': selected_row['quantity_sold_per_day']
            }
            st.success("✅ Product details refreshed successfully!")
        except Exception as e:
            st.error("❌ Failed to refresh product details. Please check your selection.")

    # Display Selected Product Details
    if st.session_state.selected_product_details:
        details = st.session_state.selected_product_details
        st.markdown(f"**Product:** {details['product_name']} - {details['variant_name']} (SKU: {details['variant_sku']})")
        st.markdown(f"**Current Inventory:** {details['current_inventory']} units")
        st.markdown(f"**Daily Demand:** {details['daily_demand']} units/day")
    else:
        st.info("ℹ️ Please select a product and click 'Refresh Details' to view its information.")

    # Form to Add Product
    with st.form("product_form"):
        st.subheader("📝 Enter Order Details")

        if st.session_state.selected_product_details:
            # Input fields for lead times and safety stock
            lead_time = st.number_input("Manufacturing Lead Time (days)", min_value=0, value=45)
            shipping_time = st.number_input("Shipping Time (days)", min_value=0, value=45)
            safety_stock_days = st.number_input("Safety Stock Time (days)", min_value=0, value=10)
            
            # **New Input Fields for In-Transit Information**
            in_transit_quantity = st.number_input("Currently In Transit Quantity", min_value=0, value=0)
            if in_transit_quantity > 0:
                expected_arrival = st.date_input(
                    "Expected Arrival Date",
                    value=datetime.today() + timedelta(days=lead_time + shipping_time)
                )
            else:
                expected_arrival = None
            submit = st.form_submit_button("📥 Add Product")
        else:
            st.warning("⚠️ Please refresh product details before adding.")
            submit = st.form_submit_button("📥 Add Product", disabled=True)

    if submit and st.session_state.selected_product_details:
        details = st.session_state.selected_product_details
        product_name = details['product_name']
        variant_name = details['variant_name']
        variant_sku = details['variant_sku']
        current_inventory = details['current_inventory']
        daily_demand = details['daily_demand']

        # Check if product is already added
        if variant_sku in [prod['SKU'] for prod in st.session_state.products]:
            st.error(f"❌ Product with SKU '{variant_sku}' is already added.")
        else:
            # Calculate order quantity and safety stock
            order_quantity, total_lead_time, safety_stock = calculate_order_quantity(
                daily_demand, lead_time, shipping_time, safety_stock_days
            )

            # Append product to session state
            st.session_state.products.append({
                'Product': product_name,
                'Variant': variant_name,
                'SKU': variant_sku,
                'Current Inventory': current_inventory,
                'Daily Demand': daily_demand,
                'Manufacturing Lead Time': lead_time,
                'Shipping Time': shipping_time,
                'Safety Stock Days': safety_stock_days,
                'Order Quantity': order_quantity,
                'Total Lead Time': total_lead_time,
                'Safety Stock': safety_stock,
                'In Transit Quantity': in_transit_quantity,
                'Expected Arrival': expected_arrival.strftime('%Y-%m-%d') if in_transit_quantity > 0 else ''
            })

            st.success(f"✅ Product '{product_name} - {variant_name}' added successfully!")

            # Generate Order Schedule for the product
            today = datetime.today()
            expected_arrival_date = datetime.combine(expected_arrival, datetime.min.time()) if in_transit_quantity > 0 else None
            schedule_df = generate_order_schedule(
                start_date=today,
                current_inventory=current_inventory,
                daily_demand=daily_demand,
                lead_time_days=lead_time,
                shipping_time_days=shipping_time,
                safety_stock_days=safety_stock_days,
                product_name=product_name,
                variant_name=variant_name,
                variant_sku=variant_sku,
                in_transit_quantity=in_transit_quantity,
                expected_arrival=expected_arrival_date
            )

            # Store the schedule in session state
            st.session_state.schedules[variant_sku] = schedule_df

            # Inform the user
            st.info(f"📅 Order schedule for '{product_name} - {variant_name}' has been generated.")

            # Optionally, reset the selected product details after adding
            st.session_state.selected_product_details = None

    # Display all added products
    if st.session_state.products:
        st.header("🗂️ All Added Products")

        # Create a DataFrame of products
        products_df = pd.DataFrame(st.session_state.products)
        display_columns = [
            'Product', 'Variant', 'SKU', 'Current Inventory', 'Daily Demand', 
            'Manufacturing Lead Time', 'Shipping Time', 'Safety Stock Days', 
            'Order Quantity', 'Total Lead Time', 'Safety Stock', 'In Transit Quantity', 'Expected Arrival'
        ]
        st.dataframe(products_df[display_columns])

        st.subheader("🔄 Manage Products")

        # Create columns for better layout
        cols = st.columns([4, 2, 2, 2, 2])

        # Header Row
        with cols[0]:
            st.markdown("**Product**")
        with cols[1]:
            st.markdown("**Variant**")
        with cols[2]:
            st.markdown("**SKU**")
        with cols[3]:
            st.markdown("**Actions**")
        with cols[4]:
            st.markdown("")  # Placeholder for alignment

        # Iterate through products and display with Remove button
        for idx, product in enumerate(st.session_state.products):
            with cols[0]:
                st.markdown(product['Product'])
            with cols[1]:
                st.markdown(product['Variant'])
            with cols[2]:
                st.markdown(product['SKU'])
            with cols[3]:
                remove_key = f"remove_{product['SKU']}"
                if st.button("🗑️ Remove", key=remove_key):
                    # Remove product from session state
                    st.session_state.products.pop(idx)
                    # Remove corresponding schedule
                    if product['SKU'] in st.session_state.schedules:
                        del st.session_state.schedules[product['SKU']]
                    st.success(f"✅ Product '{product['Product']} - {product['Variant']}' removed successfully!")
                    # To prevent multiple removals, rerun the script
                    st.experimental_rerun()
            with cols[4]:
                st.markdown("")  # Placeholder for alignment

        # Display Order Schedules for all products
        st.header("📅 Order Schedules for Next 12 Months")

        for product in st.session_state.products:
            sku = product['SKU']
            schedule = st.session_state.schedules.get(sku)

            if schedule is not None and not schedule.empty:
                st.subheader(f"Order Schedule for {product['Product']} - {product['Variant']} (SKU: {sku})")
                st.dataframe(schedule)
                # Download button for each schedule
                csv = schedule.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"⬇️ Download Order Schedule for {sku} as CSV",
                    data=csv,
                    file_name=f"{sku}_order_schedule.csv",
                    mime="text/csv",
                )
            else:
                st.info(f"ℹ️ No orders needed within the next 12 months for {product['Product']} - {product['Variant']} (SKU: {sku}).")

    else:
        st.info("📋 No products added yet. Use the forms above to add products.")

if __name__ == "__main__":
    main()
