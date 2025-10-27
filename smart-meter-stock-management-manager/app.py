def contractor_ui():
    st.header("👷 Contractor - Submit Stock Request")
    contractor_name = st.session_state.auth["name"]

    installer_name = st.text_input("Installer Name")

    st.subheader("Select Stock Items & Quantities")
    col1, col2 = st.columns(2)
    with col1:
        meter_qty = st.number_input("DN15 Meter Quantity", min_value=0, value=0, step=1)
    with col2:
        keypad_qty = st.number_input("CIU Keypad Quantity", min_value=0, value=0, step=1)

    notes = st.text_area("Notes")

    if st.button("Submit Request"):
        if not installer_name:
            st.warning("Please enter installer name")
        elif meter_qty == 0 and keypad_qty == 0:
            st.warning("Please request at least one item.")
        else:
            df = load_data()
            rid = generate_request_id()

            # Add DN15 Meter request if applicable
            if meter_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid}-M",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "DN15 Meter",
                    "Requested_Qty": meter_qty,
                    "Approved_Qty": "",
                    "Photo_Path": "",
                    "Status": "Pending Verification",
                    "Contractor_Notes": notes,
                    "City_Notes": "",
                    "Decline_Reason": "",
                    "Date_Approved": "",
                    "Date_Received": "",
                }])], ignore_index=True)

            # Add CIU Keypad request if applicable
            if keypad_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid}-K",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "CIU Keypad",
                    "Requested_Qty": keypad_qty,
                    "Approved_Qty": "",
                    "Photo_Path": "",
                    "Status": "Pending Verification",
                    "Contractor_Notes": notes,
                    "City_Notes": "",
                    "Decline_Reason": "",
                    "Date_Approved": "",
                    "Date_Received": "",
                }])], ignore_index=True)

            save_data(df)
            st.success(f"✅ Request(s) submitted under base ID {rid}")

    st.subheader("📋 My Requests")
    df = load_data()
    myreq = df[df["Contractor_Name"] == contractor_name]
    st.dataframe(myreq, use_container_width=True)
