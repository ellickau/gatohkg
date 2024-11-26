import os
import re
import requests

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask import Response

from helpers import login_required, gbp, round_to_half

#Updated on 25 Nov 2024 by Ellick 


# Configure application
app = Flask(__name__)

# Register filters to helpers.py
app.jinja_env.filters['gbp'] = gbp
app.jinja_env.filters['round_to_half'] = round_to_half

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to access SQLite database
db = SQL("sqlite:///gatohkg.db")

# Disable persistent Cookies
app.config["SESSION_PERMANENT"] = False

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# User - Registration (defualt active, user in authority)
@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration"""
    if request.method == "POST":
        # Collect form data
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        full_name = request.form.get("full_name")
        address = request.form.get("address")
        mobile = request.form.get("mobile")
        email = request.form.get("email")

        # Validate inputs
        if not all([username, password, confirmation, full_name, address, mobile, email]):
            flash("All fields are required.", "danger")
            return render_template("register.html",  username=username, full_name=full_name, address=address, mobile=mobile, email=email)
 
        # Confrim Pasword
        if password != confirmation:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", username=username, full_name=full_name, address=address, mobile=mobile, email=email)
        
        # Validate UK Mobile number format
        pattern = r"^(07\d{8,9}|(\+44)7\d{8,9})$"
        if not re.match(pattern, mobile):
            flash("Invalid UK mobile number. Use format 07XXXXXXXXX or +447XXXXXXXXX.", "danger")
            return render_template("register.html", username=username, full_name=full_name, address=address, email=email)

        # Normalize mobile to standard international format
        if mobile.startswith("07"):
            mobile = "+44" + mobile[1:]
        
        # Preprocess Inputs
        username = username.lower()  # Convert username to lowercase
        full_name = full_name.title()  # Capitalize full name

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Attempt to insert user into the database
        try:
            db.execute(
                """
                INSERT INTO users (username, hash, full_name, address, mobile, email)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                username, hashed_password, full_name, address, mobile, email
            )
            flash("Registration successful! You can now log in.", "success")
            return redirect("/login")
        except Exception as e:
            flash("Username already exists. Please choose a different username.", "danger")
            return render_template("register.html", full_name=full_name, address=address, mobile=mobile, email=email)
    
    # Render the registration form for GET requests
    return render_template("register.html")


# Login function
# check in users.status and alert users if they are inactive members
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        # Collect form inputs
        username = request.form.get("username")
        password = request.form.get("password")

        # Validate inputs
        if not username or not password:
            flash("Must provide username and password", "danger")
            return render_template("login.html")

        # Query database for user
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Verify username and password
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid username or password", "danger")
            return render_template("login.html")
        
        # Verify username is inactive
        if  rows[0]["user_status"]  != "active":
            flash("This account is inactive. Please contact Administrator for assistance.", "danger")
            return render_template("login.html")


        # On successful login, redirect without using session
        session["user_id"] = rows[0]["user_id"]
        session["username"] = rows[0]["username"]
        session["authority"] = rows[0]["authority"]
        flash("Logged in successfully", "success")
        return redirect("/")
    
    # For get requests, render login form
    return render_template("login.html")


# logout for activer user 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# User -  Order function to save or submit orders 
@app.route("/order", methods=["GET", "POST"])
@login_required
def order():
    if request.method == "POST":
        try:
            # Determine if button action is "save" or "submit"
            action = request.form.get("action")
            status = "saved" if action == "save" else "submitted"

            # Retrieve selected products
            selected_products = request.form.getlist("selected_products")
            if not selected_products:
                flash("No products selected. Please choose at least one product.", "warning")
                return redirect("/order")

            # Generate an order number only for submitted orders
            # format YYYYMMDD + username (first 4 digits Upper) + HHMMSS
            order_number = None
            if status == "submitted":
                timestamp = datetime.now().strftime("%Y%m%d")
                username_part = session["username"][:4].upper()
                unique_number = datetime.now().strftime("%H%M%S")
                order_number = f"{timestamp}{username_part}{unique_number}"

            # Initialize subtotal variable
            subtotal = 0

            # Process each selected product
            for pd_code in selected_products:
                # Validate quantity input
                try:
                    quantity = int(request.form.get(f"qty_{pd_code}", 0))
                except ValueError:
                    flash(f"Invalid quantity for product {pd_code}.", "danger")
                    return redirect("/order")

                if quantity <= 0:
                    flash(f"Quantity for product {pd_code} must be greater than zero.", "warning")
                    return redirect("/order")

                # Validate product existence
                product = db.execute("SELECT pd_price FROM products WHERE pd_code = ?", (pd_code,))
                if not product or len(product) == 0:
                    flash(f"Product with code {pd_code} not found.", "danger")
                    return redirect("/order")

                # Access price directly from the first result
                price = product[0]["pd_price"] if isinstance(product[0], dict) else product[0][0]
                order_cost = quantity * price
                subtotal += order_cost

                order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Insert the order into the database
                insert_query = """
                    INSERT INTO orders 
                    (user_id, pd_code, order_quantity, order_costs, order_status, order_payment, order_number, order_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                db.execute(insert_query, session["user_id"], pd_code, quantity, order_cost, status, "pending", order_number, order_date)

            #  Initiate 'transport-001' prodcut only if the order is submitted
            if status == "submitted":
                # Determine the delivery charge
                delivery_charge = 0
                if subtotal >= 10 and subtotal < 30:
                    delivery_charge = 5

                # Insert delivery items to orders.db as separate entry
                insert_query2 = """
                    INSERT INTO orders 
                    (user_id, pd_code, order_quantity, order_costs, order_status, order_payment, order_number, order_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                db.execute(insert_query2, session["user_id"], 'transport-001', 1, delivery_charge, status, 'pending', order_number, order_date)

                # Insert or update the delivery_details.db table
                insert_delivery_query = """
                    INSERT INTO delivery_details 
                    (order_number, delivery_address, delivery_mobile, full_name, email, order_status)
                    SELECT 
                        ?, users.address, users.mobile, users.full_name, users.email, 'submitted'
                    FROM users
                    WHERE users.user_id = ?
                    ON CONFLICT (order_number) DO UPDATE SET
                        order_status = excluded.order_status,
                        updated_at = CURRENT_TIMESTAMP;
                """
                db.execute(insert_delivery_query, order_number, session["user_id"])

            # Flash appropriate messages
            if status == "saved":
                flash("Order saved successfully!", "info")
            else:
                flash(f"Order submitted successfully! Ref: {order_number}", "success")

            return redirect("/order")

        except Exception as e:
            app.logger.error(f"Error processing order: {e}")
            flash("An error occurred while processing your order. Please try again.", "danger")
            return redirect("/order")

    # For GET requests, fetch all products except pd_copde transport-001
    products = db.execute("SELECT * FROM products WHERE pd_code != 'transport-001'")
    return render_template("order.html", products=products)


# User -  Order status for the logged-in user
# User can cancel or submit saved orders, and reviewed orders status
@app.route("/order_status", methods=["GET"])
@login_required
def order_status():
    """Display orders divided into three categories."""
    try:
        user_id = session.get("user_id")
        if not user_id:
            flash("Session expired. Please log in.", "warning")
            return redirect("/login")

        # Fetch all orders for the logined user
        orders = db.execute("""
            SELECT orders.id, orders.order_number, users.full_name, products.pd_code, products.pd_name, 
                   orders.order_quantity, orders.order_costs, orders.order_status, orders.order_payment
            FROM orders
            JOIN users ON orders.user_id = users.user_id
            JOIN products ON orders.pd_code = products.pd_code
            WHERE orders.user_id = ?
            ORDER BY orders.order_number DESC, orders.order_date DESC
        """, user_id)

        if not orders:
            flash("No orders found.", "info")
            return render_template("order_status.html", saved_orders=[], pending_orders=[], other_orders=[])

        # Categorize orders
        saved_orders = [order for order in orders if order["order_status"] == "saved"]
        pending_orders = [order for order in orders if order["order_status"] == "submitted" and order["order_payment"] == "pending"]
        other_orders = [order for order in orders if order not in saved_orders and order not in pending_orders and order["order_status"] != "cancelled"]

        return render_template("order_status.html", saved_orders=saved_orders, pending_orders=pending_orders, other_orders=other_orders)

    except Exception as e:
        app.logger.error(f"Error fetching order statuses: {e}")
        flash("An error occurred while fetching order statuses. Please try again.", "danger")
        return redirect("/")


# User - Cancel saved order by logged-in user
# Not reguired to delivery_status.db for saved orders before order submit
@app.route("/cancel_order/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    """Cancel an order and ensure it retains its reference number."""
    try:
        action = request.form.get("action")

        if action != "cancel":
            flash("Invalid action.", "danger")
            return redirect("/order_status")

        # Validate the order belongs to the logged-in user and can be cancelled
        order = db.execute("""
            SELECT * FROM orders 
            WHERE id = ? AND user_id = ? AND order_status IN ('saved', 'submitted') AND order_payment = 'pending'
        """, order_id, session["user_id"])

        if not order:
            flash("Order not found or cannot be cancelled.", "warning")
            return redirect("/order_status")
             
        # Update the order to 'cancelled' in orders.db
        db.execute("""
            UPDATE orders 
            SET order_status = 'cancelled', order_date = ?
            WHERE id = ?
        """, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id)

        flash("Order successfully cancelled.", "success")
        return redirect("/order_status")

    except Exception as e:
        app.logger.error(f"Error cancelling order: {e}")
        flash("An error occurred while cancelling the order. Please try again.", "danger")
        return redirect("/order_status")


# User - Submit selected saved orders (as batch)
# Generate order_uumber and update to orders, delivery_details db
@app.route("/submit_saved_orders", methods=["POST"])
@login_required
def submit_saved_orders():
    """Submit selected saved items as a batch."""
    try:   
        action = request.form.get("action")

        if action != "submit":
            flash("Invalid action.", "danger")
            return redirect("/order_status")
        
        user_id = session.get("user_id")
        username = session.get("username")[:4].upper()  # Get first 4 characters of the username    
        
        if not user_id or not username:
            flash("Session expired. Please log in.", "warning")
            return redirect("/login")

        # Get selected items from the form
        selected_items = request.form.getlist("selected_items")
        if not selected_items:
            flash("No items selected for submission.", "warning")
            return redirect("/order_status")

        # Generate a unique Order number 
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_number = datetime.now().strftime("%H%M%S")
        new_order_number = f"{timestamp}{username}{unique_number}"

        # Dynamically generate placeholders for the SELECT query
        placeholders = ", ".join("?" for _ in selected_items)

        # Calculate subtotal directly using SQL
        query = f"""
            SELECT SUM(order_costs) AS subtotal
            FROM orders
            WHERE id IN ({placeholders}) AND user_id = ?
        """
        result = db.execute(query, *selected_items, user_id)
        subtotal = result[0]["subtotal"]

        # Validate subtotal
        if subtotal < 10:
            flash("Minimum order of £10 required. Please consider adding more items to your order.", "warning")
            return redirect("/order_status")

        # Determine the delivery charge
        delivery_charge = 0
        if subtotal >= 10 and subtotal < 30:
            delivery_charge = 5

        # Update the status of selected items in a batch
        update_query = f"""
            UPDATE orders
            SET order_number = ?, order_status = 'submitted', order_payment = 'pending'
            WHERE id IN ({placeholders}) AND user_id = ?
        """
        db.execute(update_query, new_order_number, *selected_items, user_id)

        # Insert delivery charge as a separate entry in orders.db
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """
            INSERT INTO orders (user_id, pd_code, order_quantity, order_costs, order_status, order_payment, order_number, order_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            user_id, 'transport-001', 1, delivery_charge, 'submitted', 'pending', new_order_number, order_date,
        )

        # Insert and update the delivery_details.db
        db.execute(
            """
            INSERT INTO delivery_details (order_number, delivery_address, delivery_mobile, full_name, email, order_status)
            SELECT 
                ?, users.address, users.mobile, users.full_name, users.email, 'submitted'
            FROM users
            WHERE users.user_id = ?
            ON CONFLICT (order_number) DO UPDATE SET
                order_status = excluded.order_status,
                updated_at = CURRENT_TIMESTAMP;
            """,
            new_order_number, user_id
        )

        flash(f"Successfully submitted {len(selected_items)} items under Order Ref: {new_order_number}", "success")
        return redirect("/order_status")

    except Exception as e:
        app.logger.error(f"Error submitting saved orders: {e}")
        flash("An error occurred while submitting orders. Please try again.", "danger")
        return redirect("/order_status")


####  User - Submit Order  (obseletd !!)  #### 
@app.route("/submit_order/<int:order_id>", methods=["POST"])
@login_required
def submit_order(order_id):
    """Submit a saved order and generate an order number."""
    try:
        # Check if the order exists, belongs to the user, and is in 'saved' status
        order = db.execute("""
            SELECT * FROM orders 
            WHERE id = ? AND user_id = ? AND status = 'saved'
        """, order_id, session["user_id"])

        if not order:
            flash("Order not found or cannot be submitted.", "warning")
            return redirect("/order_status")

        # Generate a unique order number
        timestamp = datetime.now().strftime("%Y%m%d")
        username_part = session["username"][:4].upper()
        unique_number = datetime.now().strftime("%H%M%S")
        order_number = f"{timestamp}{username_part}{unique_number}"

        # Update the order to 'submitted' and add the order number
        db.execute("""
            UPDATE orders 
            SET status = 'submitted', order_number = ? 
            WHERE id = ?
        """, order_number, order_id)

        flash(f"Order successfully submitted! Ref: {order_number}", "success")
        return redirect("/order_status")

    except Exception as e:
        app.logger.error(f"Error submitting order: {e}")
        flash("An error occurred while submitting the order. Please try again.", "danger")
        return redirect("/order_status")


# User - Profile info for updating on email, address, mobile and Full name.
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]

    if request.method == "POST":
        # Fetch form data
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        full_name = request.form.get("full_name")
        address = request.form.get("address")
        mobile = request.form.get("mobile")
        email = request.form.get("email")

        # Validate password
        if not password or not confirm_password:
            flash("Password and confirmation are required.", "danger")
            return redirect("/profile")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect("/profile")

        # Update password (hash it before storing)
        hashed_password = generate_password_hash(password)
    
        # Update other fields
        db.execute(
            """
            UPDATE users
            SET full_name = :full_name,
                address = :address,
                mobile = :mobile,
                email = :email,
                hash = :hashed_password
            WHERE user_id = :user_id
            """,
            full_name=full_name,
            address=address,
            mobile=mobile,
            email=email,
            hashed_password=hashed_password,
            user_id=user_id
        )

        flash("Profile updated successfully.", "success")
        return redirect("/profile")

    # Fetch user details for GET request
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (session["user_id"],))[0]
    return render_template("profile.html", user=user)


# Admin - Manage products 
@app.route("/admin_products", methods=["GET", "POST"])
@login_required
def admin_products():
    """Admin panel for managing products."""
    if session.get("authority") != "admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    if request.method == "POST":
        # Handle actions
        selected_product_id = request.form.get("selected_product")
        action = request.form.get("action")

        if action == "edit" and selected_product_id:
            return redirect(f"/admin_edit_product/{selected_product_id}")
        elif action == "add":
            return redirect("/admin_add_product")

        flash("Please select a product to edit or choose to add a new product.", "warning")
        return redirect("/admin_products")

    # Fetch all products for display
    products = db.execute("SELECT * FROM products ORDER BY id ASC")
    return render_template("admin_products.html", products=products)


# Admin - Edit a product (redirect from manage products )
@app.route("/admin_edit_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def admin_edit_product(product_id):
    """Edit product information."""
    if session.get("authority") != "admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    if request.method == "POST":
        # Update product details
        pd_name = request.form.get("pd_name")
        pd_code = request.form.get("pd_code")
        pd_price = float(request.form.get("pd_price"))
        description = request.form.get("description")
        pd_status = request.form.get("pd_status")

        db.execute("""
            UPDATE products
            SET pd_name = ?, pd_code = ?, pd_price = ?, description = ?, pd_status = ?
            WHERE id = ?
        """, pd_name, pd_code, pd_price, description, pd_status, product_id)

        flash("Product information updated successfully.", "success")
        return redirect("/admin_products")

    # Fetch product details for editing
    product = db.execute("SELECT * FROM products WHERE id = ?", product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect("/admin_products")
    return render_template("admin_edit_product.html", product=product[0])


# Admin - Add new product (redirect from manage products)
@app.route("/admin_add_product", methods=["GET", "POST"])
@login_required
def admin_add_product():
    """Add a new product."""
    if session.get("authority") != "admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    if request.method == "POST":
        pd_name = request.form.get("pd_name")
        pd_code = request.form.get("pd_code")
        pd_price = float(request.form.get("pd_price"))
        description = request.form.get("description") or ""  # Default to empty string
        pd_status = request.form.get("pd_status")
        pd_picture = request.form.get("pd_picture") or "img/default-product.jpg"  # Default picture

        try:
            # Insert new product into database
            db.execute("""
                INSERT INTO products (pd_name, pd_code, pd_price, description, pd_status, pd_picture)
                VALUES (?, ?, ?, ?, ?, ?)
            """, pd_name, pd_code, pd_price, description, pd_status, pd_picture)

            flash("New product added successfully.", "success")
            return redirect("/admin_products")
        except Exception as e:
            app.logger.error(f"Error adding product: {e}")
            flash("An error occurred while adding the product. Please try again.", "danger")

    return render_template("admin_add_product.html")


# Admin - Manage users 
@app.route("/admin_users", methods=["GET", "POST"])
@login_required
def admin_users():
    """Admin panel for managing users."""
    if session.get("authority") != "admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    if request.method == "POST":
        # Handle edit or delete actions
        selected_user_id = request.form.get("selected_user")
        action = request.form.get("action")

        if not selected_user_id:
            flash("No user selected. Please select a user to proceed.", "warning")
            return redirect("/admin_users")

        if action == "edit":
            # Redirect to edit user page
            return redirect(f"/admin_edit_user/{selected_user_id}")
        return redirect("/admin_users")

    # Fetch all users for display
    users = db.execute("SELECT * FROM users")
    return render_template("admin_users.html", users=users)

# Admin - Edit user (redirect from manager users)
@app.route("/admin_edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin_edit_user(user_id):
    """Edit user information."""
    if session.get("authority") != "admin":
        flash("You do not have permission to access this page.", "danger")
        return redirect("/")

    if request.method == "POST":
        # Update user details
        full_name = request.form.get("full_name")
        address = request.form.get("address")
        mobile = request.form.get("mobile")
        email = request.form.get("email")
        authority = request.form.get("authority")
        user_status = request.form.get("user_status")

        db.execute("""
            UPDATE users
            SET full_name = ?, address = ?, mobile = ?, email = ?, authority = ?, user_status = ?
            WHERE user_id = ?
        """, full_name, address, mobile, email, authority, user_status, user_id )

        flash("User information updated successfully.", "success")
        return redirect("/admin_users")

    # Fetch the user details for editing
    user = db.execute("SELECT * FROM users WHERE user_id = ?", user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect("/admin_users")
    return render_template("admin_edit_user.html", user=user[0])


# Dashbaord - View all orders in different categories and take actions
@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Render the admin dashboard with categorized orders."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/")

    try:
        # Fetch saved orders
        saved_orders = db.execute("""
            SELECT orders.id, orders.user_id, users.full_name, products.pd_code, products.pd_name,
                   orders.order_quantity, orders.order_costs, orders.order_date,
                   julianday('now') - julianday(orders.order_date) AS day_holding
            FROM orders
            JOIN users ON orders.user_id = users.user_id
            JOIN products ON orders.pd_code = products.pd_code
            WHERE orders.order_status = 'saved'
            ORDER BY orders.order_date ASC;
        """)

        # Fetch submitted and pending payment orders
        submitted_orders = db.execute("""
            SELECT orders.order_number, orders.user_id, users.full_name,
                   SUM(CASE WHEN orders.pd_code != 'transport-001' THEN orders.order_quantity ELSE 0 END) AS total_qty,
                   SUM(orders.order_costs) AS total_costs,
                   orders.order_payment, orders.order_status, delivery_details.admin_action,
                   julianday('now') - julianday(MIN(orders.order_date)) AS day_holding
            FROM orders
            JOIN delivery_details ON orders.order_number = delivery_details.order_number
            JOIN users ON orders.user_id = users.user_id
            WHERE orders.order_status = 'submitted' AND orders.order_payment = 'pending' AND delivery_details.admin_action != 'closed'
            GROUP BY orders.order_number
            ORDER BY MIN(orders.order_date) ASC;
        """)

        # Fetch in preparation orders
        in_preparation_orders = db.execute("""
            SELECT orders.order_number, orders.user_id, users.full_name,
                   SUM(CASE WHEN orders.pd_code != 'transport-001' THEN orders.order_quantity ELSE 0 END) AS total_qty,
                   SUM(orders.order_costs) AS total_costs,
                   orders.order_payment, orders.order_status, delivery_details.admin_action,
                   julianday('now') - julianday(MIN(orders.order_date)) AS day_holding
            FROM orders
            JOIN delivery_details ON orders.order_number = delivery_details.order_number
            JOIN users ON orders.user_id = users.user_id
            WHERE orders.order_status = 'in preparation' AND orders.order_payment = 'paid' AND delivery_details.admin_action != 'closed'
            GROUP BY orders.order_number
            ORDER BY MIN(orders.order_date) ASC;
        """)


        # Fetch in delivered order
        view_delivered = db.execute("""
            SELECT orders.order_number, orders.user_id, users.full_name,
                   SUM(CASE WHEN orders.pd_code != 'transport-001' THEN orders.order_quantity ELSE 0 END) AS total_qty,
                   SUM(orders.order_costs) AS total_costs,
                   orders.order_payment, orders.order_status, delivery_details.admin_action,  
                   delivery_details.updated_at
            FROM orders
            JOIN delivery_details ON orders.order_number = delivery_details.order_number AND delivery_details.admin_action = 'closed'
            JOIN users ON orders.user_id = users.user_id
            WHERE orders.order_status = 'delivered' AND orders.order_payment = 'paid'
            GROUP BY orders.order_number
            ORDER BY MIN(orders.order_date) DESC;
        """)

        # Fetch cancelled orders
        cancelled_orders = db.execute("""
            SELECT orders.id, orders.user_id, orders.order_number,users.full_name, products.pd_code, products.pd_name,
                   orders.order_quantity, orders.order_costs, orders.order_payment, orders.order_status, 
                   orders.order_date
            FROM orders
            JOIN users ON orders.user_id = users.user_id
            JOIN products ON orders.pd_code = products.pd_code
            WHERE orders.order_status = 'cancelled'
            ORDER BY orders.order_date ASC;
        """)

        return render_template(
            "dashboard.html",
            saved_orders=saved_orders,
            submitted_orders=submitted_orders,
            in_preparation_orders=in_preparation_orders,
            view_delivered=view_delivered,
            cancelled_orders=cancelled_orders
        )
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return redirect("/")


# Dashboard - Cancel_saved_orders by admin
@app.route("/dashboard/cancel_saved", methods=["POST"])
@login_required
def cancel_saved_orders():
    """Cancel selected saved orders."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/")
    
    last_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    selected_orders = request.form.getlist("selected_orders")
    if not selected_orders:
        flash("No orders selected for cancellation.", "warning")
        return redirect("/dashboard")

    try:
        db.execute(
            "UPDATE orders SET order_status = ? , order_date = ? WHERE id IN ({})".format(
                ", ".join("?" * len(selected_orders))
            ),
            "cancelled", last_date, *selected_orders,
        )
        flash(f"Successfully cancelled {len(selected_orders)} orders.", "success")
        return redirect("/dashboard")
    except Exception as e:
        app.logger.error(f"Error canceling saved orders: {e}")
        flash("An error occurred while canceling orders. Please try again.", "danger")
        return redirect("/dashboard")

# Dashbaord - Vanaged or cancelled submitted orders by admin
# Redirect to edit_order for updated delivery detail
@app.route("/dashboard/manage_submitted", methods=["POST"])
@login_required
def manage_submitted():
    """Manage submitted orders: edit or cancel."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    action = request.form.get("action")
    selected_order = request.form.get("selected_orders")

    # Validate input
    if not selected_order:
        flash("No order selected.", "warning")
        return redirect("/dashboard")

    if action == "edit":
        # Redirect to edit functionality
        return redirect(f"/dashboard/edit_order/{selected_order}")
    
    elif action == "cancel":
        try:

            # Update all rows in orders table with the same order_number
            db.execute("""
                UPDATE orders
                SET order_status = 'cancelled', order_date = ?
                WHERE order_number = ?
            """, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_order)

            # Update the single row in delivery_details table
            db.execute("""
                UPDATE delivery_details
                SET order_status = 'cancelled', admin_action = 'closed', updated_at = ?
                WHERE order_number = ?
            """, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_order)

            flash("Order cancelled successfully.", "success")
        
        except Exception as e:
            app.logger.error(f"Error cancelling order: {e}")
            flash("Failed to cancel order. Please try again.", "danger")
    else:
        flash("Invalid action.", "danger")

    return redirect("/dashboard")

# Dashbaord - Managed submitted, in preparation orders by admin
@app.route("/dashboard/edit_order/<string:order_number>", methods=["GET", "POST"])
@login_required
def edit_order(order_number):
    """Edit order details dynamically based on current status."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    if request.method == "POST":
        # Fetch form inputs
        delivery_address = request.form.get("delivery_address")
        delivery_mobile = request.form.get("delivery_mobile")
        full_name = request.form.get("full_name")
        payment_status = request.form.get("payment_status")  # Input from form
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Fetch current order status
        order_details = db.execute("SELECT order_status FROM delivery_details WHERE order_number = ?", order_number)
        if not order_details:
            flash("Order not found.", "danger")
            return redirect("/dashboard")

        current_status = order_details[0]["order_status"]

        # Fetch payment status from the orders table
        order_payment_data = db.execute("SELECT order_payment FROM orders WHERE order_number = ?", order_number)
        if not order_payment_data:
            flash("Order payment details not found.", "danger")
            return redirect("/dashboard")

        # Determine the next step based on the current status
        next_status = None
        admin_action = "validated"  # Default admin_action for status changes
        if current_status == "submitted":
            next_status = "in preparation"
            # Validation for submitted -> in preparation
            if payment_status != "paid":
                flash("Order cannot move to 'In Preparation' unless payment status is 'Paid'.", "warning")
                return redirect(f"/dashboard/edit_order/{order_number}")
        elif current_status == "in preparation":
            next_status = "delivered"
            admin_action = "closed"  # Admin action changes to "closed" for delivery

        # Update delivery details
        try:
            db.execute("""
                UPDATE delivery_details
                SET delivery_address = ?, delivery_mobile = ?, full_name = ?, 
                    admin_action = ?, order_status = ?, updated_at = ?
                WHERE order_number = ?
            """, delivery_address, delivery_mobile, full_name, admin_action, next_status, timestamp, order_number)

            # Update orders table
            db.execute("""
                UPDATE orders
                SET order_payment = ?, order_status = ?, order_date = ?
                WHERE order_number = ?
            """, payment_status, next_status, timestamp, order_number)

            app.logger.debug(f"Order {order_number} updated successfully.")
            flash(f"Order updated successfully. Status is now '{next_status}'.", "success")
        except Exception as e:
            app.logger.error(f"Error updating order: {e}")
            flash("An error occurred while updating the order.", "danger")
            return redirect(f"/dashboard/edit_order/{order_number}")

        return redirect("/dashboard")

    # Fetch order details
    order_details = db.execute("SELECT * FROM delivery_details WHERE order_number = ?", order_number)
    order_items = db.execute("""
        SELECT orders.*, products.pd_name, products.pd_price
        FROM orders
        JOIN products ON orders.pd_code = products.pd_code
        WHERE orders.order_number = ?
    """, order_number)

    # Fetch order payment status
    order_payment = db.execute("SELECT order_payment FROM orders WHERE order_number = ?", order_number)[0]["order_payment"]

    if not order_details:
        flash("Order not found.", "danger")
        return redirect("/dashboard")

    # Include payment_status from orders
    order = {**order_details[0], "order_items": order_items, "payment_status": order_payment}
    return render_template("dashboard_edit_order.html", order=order)

# Dashbaord - managed in preparation orders by admin
@app.route("/dashboard/manage_in_preparation", methods=["POST"])
@login_required
def manage_in_preparation_orders():
    """Manage in preparation orders."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    action = request.form.get("action")
    selected_order = request.form.get("selected_orders")

    if not selected_order:
        flash("No order selected.", "warning")
        return redirect("/dashboard")

    if action == "edit":
        # Redirect to edit page
        return redirect(f"/dashboard/edit_order/{selected_order}")
    elif action == "cancel":
        # Cancel the order
        try:
            db.execute("""
                UPDATE orders
                SET order_status = 'cancelled', order_date = ?
                WHERE order_number = ?
            """, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_order)

            db.execute("""
                UPDATE delivery_details
                SET order_status = 'cancelled', admin_action = 'closed', updated_at = ?
                WHERE order_number = ?
            """, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_order)

            flash("Order cancelled successfully.", "success")
        except Exception as e:
            app.logger.error(f"Error cancelling order: {e}")
            flash("Failed to cancel order. Please try again.", "danger")
    else:
        flash("Invalid action selected.", "danger")

    return redirect("/dashboard")

# Dashboard - viewed on delivered order
@app.route("/dashboard/view_delivered", methods=["GET", "POST"])
@login_required
def view_delivered_orders():
    """View delivered order details."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    # Handle both GET and POST requests
    if request.method == "POST":
        selected_order = request.form.get("selected_orders")
    elif request.method == "GET":
        selected_order = request.args.get("selected_orders")

    if not selected_order:
        flash("No order selected.", "warning")
        return redirect("/dashboard")

    try:
        # Fetch order details
        order_details = db.execute("""
            SELECT orders.order_number, orders.user_id, users.full_name, users.email,
                delivery_details.delivery_address, delivery_details.delivery_mobile,
                delivery_details.admin_action, orders.order_status, orders.order_payment,
                delivery_details.updated_at,
                SUM(orders.order_costs) AS total_costs, SUM(orders.order_quantity) AS total_qty
            FROM orders
            JOIN delivery_details ON orders.order_number = delivery_details.order_number
            JOIN users ON orders.user_id = users.user_id
            WHERE orders.order_number = ?
            GROUP BY orders.order_number
        """, selected_order)

        # Fetch individual items, including transport-001
        order_items = db.execute("""
            SELECT orders.pd_code, products.pd_name, products.pd_price, orders.order_quantity
            FROM orders
            LEFT JOIN products ON orders.pd_code = products.pd_code
            WHERE orders.order_number = ?
        """, selected_order)

        if not order_details:
            flash("Order not found.", "warning")
            return redirect("/dashboard")

        # Exclude transport-001 from total_qty calculation
        total_qty = sum(item["order_quantity"] for item in order_items if item["pd_code"] != "transport-001")

        # Include transport-001 in total_costs
        total_costs = sum(item["pd_price"] * item["order_quantity"] if item["pd_price"] else item["order_quantity"]
                        for item in order_items)
        
        return render_template(
            "dashboard_delivered.html",
            order=order_details[0],
            order_items=order_items,
            total_qty=total_qty,
            total_costs=total_costs,
        )

    except Exception as e:
        app.logger.error(f"Error fetching delivered order: {e}")
        flash("An error occurred while fetching order details.", "danger")
        return redirect("/dashboard")


# Dashbaord - viewed on cancelled order by admin
@app.route("/dashboard/view_cancelled", methods=["GET"])
@login_required
def view_cancelled_orders():
    """View all cancelled orders."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    try:
        # Fetch cancelled orders
        cancelled_orders = db.execute("""
            SELECT orders.id, orders.user_id, users.full_name, products.pd_code, products.pd_name,
                   orders.order_quantity, orders.order_costs, orders.order_payment, orders.order_status, 
                   orders.order_date
            FROM orders
            JOIN users ON orders.user_id = users.user_id
            JOIN products ON orders.pd_code = products.pd_code
            WHERE orders.order_status = 'cancelled'
            ORDER BY orders.order_date DESC
        """)

        return render_template("view_cancelled_orders.html", cancelled_orders=cancelled_orders)
    except Exception as e:
        app.logger.error(f"Error fetching cancelled orders: {e}")
        flash("An error occurred while fetching cancelled orders.", "danger")
        return redirect("/dashboard")

# Admin - Summary Monthly report for orders sorted by different stages
@app.route("/admin_report", methods=["GET"])
@login_required
def admin_report():
    """Generate a monthly summary report for admin."""
    if session.get("authority") != "admin":
        flash("Unauthorized access.", "danger")
        return redirect("/dashboard")

    try:
        # Query for monthly saved orders
        saved_orders = db.execute("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   COUNT(id) AS count
            FROM orders
            WHERE order_status = 'saved'
            GROUP BY month
            ORDER BY month ASC
        """)

        # Query for monthly cancelled orders
        cancelled_orders = db.execute("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   COUNT(id) AS count
            FROM orders
            WHERE order_status = 'cancelled'
            GROUP BY month
            ORDER BY month ASC
        """)

        # Query for monthly submitted orders
        submitted_orders = db.execute("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   SUM(CASE WHEN pd_code != 'transport-001' THEN order_quantity ELSE 0 END) AS total_qty,
                   SUM(order_costs) AS total_costs
            FROM orders
            WHERE order_status = 'submitted'
            GROUP BY month
            ORDER BY month ASC
        """)

        # Query for monthly in preparation orders
        in_preparation_orders = db.execute("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   SUM(CASE WHEN pd_code != 'transport-001' THEN order_quantity ELSE 0 END) AS total_qty,
                   SUM(order_costs) AS total_costs
            FROM orders
            WHERE order_status = 'in preparation'
            GROUP BY month
            ORDER BY month ASC
        """)

        # Query for monthly delivered orders
        delivered_orders = db.execute("""
            SELECT strftime('%Y-%m', order_date) AS month,
                   SUM(CASE WHEN pd_code != 'transport-001' THEN order_quantity ELSE 0 END) AS total_qty,
                   SUM(order_costs) AS total_costs
            FROM orders
            WHERE order_status = 'delivered'
            GROUP BY month
            ORDER BY month ASC
        """)

        # Combine data for rendering
        report_data = {
            "saved_orders": saved_orders,
            "cancelled_orders": cancelled_orders,
            "submitted_orders": submitted_orders,
            "in_preparation_orders": in_preparation_orders,
            "delivered_orders": delivered_orders,
        }

        return render_template("admin_report.html", report_data=report_data)
    except Exception as e:
        app.logger.error(f"Error generating report: {e}")
        flash("An error occurred while generating the report.", "danger")
        return redirect("/dashboard")


if __name__ == '__main__':
    app.run(debug=True)