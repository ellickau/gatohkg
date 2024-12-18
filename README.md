# GatoHKG Order Management System

#### Video Demo:  [https://youtu.be/p8SzQ5AWWxw]

#### Demon site [https://ellickau.pythonanywhere.com/]

#### Description:

**GatoHKG Order Management System** is a web application tailored for a small-to-medium-sized bakery and pastry sho, named GatoHKG. The system facilitates user registration, login, order placement, order tracking, and administrative management. Built with Flask and SQLite, it employs web technologies such as HTML5, CSS3, and Bootstrap 5, offering a scalable and user-friendly solution for streamlined business operations.

## Overall Features

### General Features:
- **User Registration and Login**: Enables account creation and management for users.
- **Order Placement**: Allows users to place, save drafts, and submit orders efficiently.
- **Order Tracking**: Provides real-time order status updates for users.
- **Admin Management tools**: Grants administrators advanced capabilities for managing users, products, and orders.
- **Admin Dashboard**: Displays comprehensive insights into all orders across various stages (e.g., pending payment, in preparation, delivered, or cancelled).


### Key Functionalities:

#### 1. User Management: (All)
- Enable users to register with required details like name, address, mobile number, and email.
- Allow users to update their profiles and reset passwords.

#### 2. Order Management: (Users)
- Users can place, save, or submit orders.
- Automatically generates order numbers and calculates delivery charges based on predefined rules.
- Users can cancel saved orders that have not been processed.

#### 3. Product Management (Admin)
- Add, update, and manage product details such as name, price, description, and availability status.

#### 4. Users Management (Admin)
- Add, edit, and manage user profiles, including name, address, mobile number, authority (user/admin), and activity status (active/inactive).

#### 5. Order Tracking (Admin)
- Monitor orders by categories:
  - **Saved**: Admins can cancel selected orders.
  - **Submitted**: Cancel orders, edit delivery details, and update payment statuses to "paid."
  - **In Preparation**: Validate delivery details, confirm delivery, and close the order.
  - **Delivered**: View delivery details and breakdown of order items.

#### 6. Dashboard (Admin)
- Categorized views of orders.
- Options to edit delivery details, update payment statuses, and manage cancelled or completed orders.

#### 7. Monthly Reports (Admin)
- Generate reports summarizing orders across various stages to gain business insights.


## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with CS50 Library for database operation.
- **Frontend**: HTML, CSS, Bootstrap, Jinja2 for templating.
- **Libraries**:
  - `flask-session` for session management
  - `werkzeug.security` for password hashing
  - `datetime` for managing timestamps
  - Regular Expressions (`re`) for input validation

## Installation


1. **Clone the Repository**:
   Clone the repository using CS50 IDE environment:
   
   git clone <https://github.com/code50/81462764>
   (for cs50X final project submisson and UAT prupose )


2. **Set up Python Environment**:
    - python3 -m venv env
    - source env/bin/activate
    - pip install -r requirements.txt

3. **Set up the Database**:
   - Ensure SQLite is installed on your system.
   - Create a new database file or use the provided gatohkg.db file.

4. **Run the Application**:
    - flask run
    - Access the application at https://animated-space-train-4r94gj45px9h7qp5-5000.app.github.dev/

5. **Future Enhancements**:
    - Deploying the application on a public web server for wider accessibility.
    - Adding SMS and email notifications features for order status updates.
    - Integrating third-party payment systems like PayPal or online credit card payment.
    - Enhancing the UI with more interactive features to improve users' experience.
    - Strengthening backend security to protect sensitive user data.

6. **Acknowledgements**:
    - CS50 Library: Simplified database operations.
    - Prof. David J. Malan: For his inspiring teachings and course materials in CS50x.
    - ChatGPT and CS50.AI: Assisted with debugging and overcoming coding challenges.
    - Family Support: Special thanks to my wife, Ann, and family for their encouragement and motivation to complete this project.
"# gatohkg" 
"# gatohkg" 
"# gatohkg" 
