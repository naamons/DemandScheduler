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
    variant_sku
):
    total_lead_time = lead_time_days + shipping_time_days
    safety_stock = daily_demand * safety_stock_days
    reorder_point = (daily_demand * total_lead_time) + safety_stock
    order_quantity = (daily_demand * total_lead_time) + safety_stock

    schedule = []
    date = start_date
    end_date = start_date + timedelta(days=365)  # 12 months

    while date < end_date:
        # Consume daily demand
        current_inventory -= daily_demand

        # Check if inventory has reached reorder point
        if current_inventory <= reorder_point:
            # Schedule next order
            order_date = date
            arrival_date = order_date + timedelta(days=total_lead_time)
            schedule.append({
                'Product': product_name,
                'Variant': variant_name,
                'SKU': variant_sku,
                'Order Date': order_date.strftime('%Y-%m-%d'),
                'Arrival Date': arrival_date.strftime('%Y-%m-%d'),
                'Order Quantity': order_quantity
            })
            # Update inventory upon order arrival
            current_inventory += order_quantity

        date += timedelta(days=1)

    return pd.DataFrame(schedule)

# Initialize session state for products and schedules
if 'products' not in st.session_state:
    st.session_state.products = []
if 'schedules' not in st.session_state:
    st.session_state.schedules = {}

# Streamlit App
def main():
    st.set_page_config(page_title="Inventory Order Management", layout="wide")
    st.title("📦 Inventory Order Management App")

    st.sidebar.header("🔄 Upload Demand CSV")
    uploaded_file = st.sidebar.file_uploader("Upload your demand CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            demand_df = pd.read_csv(uploaded_file)
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

    # Form to add a product
    with st.form("product_form"):
        # Dropdown to select product by name or SKU
        product_options = demand_df.apply(
            lambda row: f"{row['product_title']} - {row['variant_title']} (SKU: {row['variant_sku']})", axis=1
        )
        selected_product = st.selectbox("Select Product", options=product_options)

        # Extract the selected product's details
        selected_index = product_options.index[demand_df.apply(
            lambda row: f"{row['product_title']} - {row['variant_title']} (SKU: {row['variant_sku']})", axis=1
        ) == selected_product][0]
        selected_row = demand_df.iloc[selected_index]
        product_name = selected_row['product_title']
        variant_name = selected_row['variant_title']
        variant_sku = selected_row['variant_sku']
        current_inventory = selected_row['ending_quantity']
        daily_demand = selected_row['quantity_sold_per_day']

        # Display selected product details
        st.markdown(f"**Product:** {product_name} - {variant_name} (SKU: {variant_sku})")
        st.markdown(f"**Current Inventory:** {current_inventory} units")
        st.markdown(f"**Daily Demand:** {daily_demand} units/day")

        # Input fields for lead times and safety stock
        lead_time = st.number_input("Manufacturing Lead Time (days)", min_value=0, value=45)
        shipping_time = st.number_input("Shipping Time (days)", min_value=0, value=45)
        safety_stock_days = st.number_input("Safety Stock Time (days)", min_value=0, value=10)
        submit = st.form_submit_button("📥 Add Product")

    if submit:
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
                'Safety Stock': safety_stock
            })

            st.success(f"✅ Product '{product_name} - {variant_name}' added successfully!")

            # Generate Order Schedule for the product
            today = datetime.today()
            schedule_df = generate_order_schedule(
                start_date=today,
                current_inventory=current_inventory,
                daily_demand=daily_demand,
                lead_time_days=lead_time,
                shipping_time_days=shipping_time,
                safety_stock_days=safety_stock_days,
                product_name=product_name,
                variant_name=variant_name,
                variant_sku=variant_sku
            )

            # Store the schedule in session state
            st.session_state.schedules[variant_sku] = schedule_df

            # Inform the user
            st.info(f"📅 Order schedule for '{product_name} - {variant_name}' has been generated.")

    # Display all added products
    if st.session_state.products:
        st.header("🗂️ All Added Products")

        # Create a DataFrame of products
        products_df = pd.DataFrame(st.session_state.products)
        display_columns = [
            'Product', 'Variant', 'SKU', 'Current Inventory', 'Daily Demand', 
            'Manufacturing Lead Time', 'Shipping Time', 'Safety Stock Days', 
            'Order Quantity', 'Total Lead Time', 'Safety Stock'
        ]
        st.dataframe(products_df[display_columns])

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
        st.info("📋 No products added yet. Use the form above to add products.")

if __name__ == "__main__":
    main()
