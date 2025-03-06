from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_marshmallow import Marshmallow
from datetime import date
from typing import List
from marshmallow import ValidationError, fields
from sqlalchemy import select, delete

app = Flask(__name__) # Creates an instance of our flask application.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Preciosa2016!@localhost/e_commerce_db2'


# Each class in our Model is going to inherit from the Base class, which inherits from SQL Alchemys Declarative Base class.
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)
#=================================== MODELS ======================================
class Customer(Base):
    __tablename__ = 'customer' 

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    email: Mapped[str] = mapped_column(db.String(225))
    address: Mapped[str] = mapped_column(db.String(225))
    orders: Mapped[List["Orders"]] = db.relationship("Orders",back_populates='customer')


'''
ASSOCIATION TABLE: order_products
Because we have many-to-many relationships, an association table is required.
This table facilitates the relationship from one order to many products, or many products back to one order.
This only includes foreign keys, so we don't need to create a complicated class model for it.
'''
order_products = db.Table(
    "Order_Products",
    Base.metadata, 
    db.Column('order_id', db.ForeignKey('orders.id')),
    db.Column('product_id', db.ForeignKey('products.id'))
)

class Orders(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customer.id'))
    # Creates a one-to-many relationship to the customer table
    customer: Mapped['Customer'] = db.relationship(back_populates='orders')
    products: Mapped[List['Products']] = db.relationship(secondary=order_products, back_populates='orders')

class Products(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(225), nullable=False) 
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    orders: Mapped[List['Orders']] = db.relationship(secondary=order_products, back_populates='products')

#=================================== SCHEMAS ======================================

class CustomerSchema(ma.SQLAlchemyAutoSchema): 
    class Meta:
        model = Customer


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Products

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Orders
        include_fk = True # Need this because Auto Schemas don't automatically recognize foreign keys(custoemer_id)

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

#=================================== API ROUTES ======================================

@app.route('/')
def home():
    return "Home"

# Get all customers using a GET methods
@app.route("/customers", methods=['GET'])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars() # Execute query and convert row objects into scalar objects (Python usable)
    customers = result.all() # Packs objects into a list
    return jsonify(customers_schema.dump(customers))

#Get Specific customer using GET method and dynamic route
@app.route("/customers/<int:id>", methods=['GET'])
def get_customer(id):
    
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first() #first() grabs the first object return

    if result is None:
        return jsonify({"Error": "Customer not found"}), 404
    
    return customer_schema.jsonify(result)

# Create customer with POST request
@app.route("/customers", methods=["POST"])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], address=customer_data['address'])
    db.session.add(new_customer)
    db.session.commit()

    return jsonify({"Message": "New customer added successfully", 
                    "customer": customer_schema.dump(new_customer)}), 201

# Update customer by ID with PUT
@app.route("/customers/<int:id>", methods=["PUT"])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.address= customer_data['address']
    db.session.commit()
    return jsonify({"message": "Customer details updated successfuly"}), 200  

# DELETE CUSTOMER BY ID
@app.route("/customers/<int:id>", methods=["DELETE"]) 
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    
    try:
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'message': f'Customer with ID {id} has been deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500



#=============== API ROUTES: Products ==================
# CREATE PRODUCT
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_product = Products(product_name = product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"Messages": "New product added!",
                   "product": product_schema.dump(new_product)}), 201

# GET PRODUCTS
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars()
    products = result.all()
    return products_schema.jsonify(products)

# GET PRODUCT BY ID
@app.route('/products/<int:id>', methods=['GET'])
def read_product(id):
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"error": "Product not found"}), 401
    return jsonify({"id": product.id, "name": product.product_name, "price": product.price}), 200


#UPDATE PRODUCT BY ID
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    data = request.get_json()
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    product.product_name = data.get('product_name', product.product_name)
    product.price = data.get('price', product.price)
    db.session.commit()
    return jsonify({"message": "Product updated successfull", "product": {"id": product.id, "name": product.product_name, "price": product.price}}), 200
 
# DELETE PRODUCT BY ID
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Products, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200


#=============== API ROUTES: Order Operations ==================
#CREATE an ORDER
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    # Retrieve the customer by its id.
    customer = db.session.get(Customer, order_data['customer_id'])
    
    # Check if the customer exists.
    if customer:
        new_order = Orders(order_date=order_data['order_date'], customer_id = order_data['customer_id'])

        db.session.add(new_order)
        db.session.commit()

        return jsonify({"Message": "New Order Placed!",
                        "order": order_schema.dump(new_order)}), 201
    else:
        return jsonify({"message": "Invalid customer id"}), 400

#ADD ITEM TO ORDER
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product(order_id, product_id):
    order = db.session.get(Orders, order_id) #can use .get when querying using Primary Key
    product = db.session.get(Products, product_id)

    if order and product: #check to see if both exist
        if product not in order.products: #Ensure the product is not already on the order
            order.products.append(product) #create relationship from order to product
            db.session.commit() #commit changes to db
            return jsonify({"Message": "Successfully added item to order."}), 200
        else:#Product is in order.products
            return jsonify({"Message": "Item is already included in this order."}), 400
    else:#order or product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400

# REMOVE A PRODUCT FROM AN ORDER
@app.route('/orders/<int:order_id>/products/<int:product_id>', methods=['DELETE'])
def remove_product_from_order(order_id, product_id):
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)

    if not order or not product:
        return jsonify({"error": "Order or Product not found"}), 404
    
    if product in order.products:
        order.products.remove(product)
        db.session.commit()
        return jsonify({"message": f"Product {product_id} removed from Order {order_id}"}), 200
    else: 
        return jsonify({"error": "Product not found in the order"}), 400
    
# GET ALL ORDERS FOR A SPECIFIC USER
@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_for_user(user_id):
    query = select(Orders).where(Orders.customer_id == user_id)
    result = db.session.execute(query).scalars().all()

    if not result:
        return jsonify({"message": "No orders found for this user"}), 404
    
    return orders_schema.jsonify(result), 200

# GET ALL PRODUCTS IN A SPECIFIC ORDER
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_in_order(order_id):
    order = db.session.get(Orders, order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    return products_schema.jsonify(order.products), 200



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)