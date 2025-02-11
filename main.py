import mysql.connector
from flask import Flask, render_template,request,redirect,url_for,session,flash
from werkzeug.utils import secure_filename
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "mysecretkey"

# forming connection with database
con = mysql.connector.connect(host="localhost", user="root", password="mypassword", database="mydatabase")

#index page
@app.route("/")
def home():
    cursor = con.cursor(dictionary=True)
    cursor.execute("select * from categories")
    categories = cursor.fetchall()
    
    #fetch specific featured products by their ids
    featured_ids = [48,49,50,51,52,53]
    sql = "select product_id, name, image_url, price from products where product_id in(%s,%s,%s,%s,%s,%s)"
    cursor.execute(sql,featured_ids)
    featured_products = cursor.fetchall()
    
    return render_template("index.html",categories=categories, featured_products=featured_products)

#user register
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        address = request.form["address"]
        city = request.form["city"]
        phone_number = request.form["phone_number"]
        
        cursor = con.cursor()
        sql = "insert into users (full_name,email,password,address,city,phone_number) values (%s, %s, %s, %s, %s, %s)"
        val = (full_name,email,password,address,city,phone_number)
        cursor.execute(sql,val)
        con.commit()
        cursor.close()
        return redirect(url_for('login'))
    
    return render_template("register.html")

   
# login route
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        remember_me = "remember" in request.form
        print(email,password)
        
        #first, check if the user is an admin
        cursor = con.cursor(dictionary=True)
        sql_admin = "select * from admin where email = %s and password=%s"
        cursor.execute(sql_admin,(email,password))
        admin = cursor.fetchone()
        cursor.close()
        
        if admin:
            session["admin_id"] = admin["admin_id"]
            session["admin_email"] = admin["email"]
            print(email,password)
            
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=7)
            return redirect(url_for("admin_dashboard"))
        
        # if not an admin, check if it's a user
        cursor = con.cursor(dictionary=True)
        sql_user = "select * from users where email = %s and password=%s"
        cursor.execute(sql_user,(email,password))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=7)
            return redirect(url_for("home"))
        
        else:
            flash("invalid login credentials.","error")
            return redirect(url_for("login"))
    else:
        return render_template("login.html")   
    
#user logout route
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))     
   
#admin dashboard     
@app.route("/admin/dashboard")    
def admin_dashboard():
    if "admin_id" not in session:
        flash("please log in as admin to access the bashboard.","error")
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    
    #fetch the summary counts
    cursor.execute("select count(*) as total from products")
    total_products = cursor.fetchone()["total"]
    
    cursor.execute("select count(*) as total from categories")
    total_categories = cursor.fetchone()["total"]
    
    cursor.execute("select count(*) as total from users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("select count(*) as total from orders")
    total_orders = cursor.fetchone()["total"]
    
    #fetch latest orders 
    sql = ''' select o.order_id, u.full_name as user_name,o.total_amount,o.order_status,o.created_at
    from orders o
    join users u on o.user_id = u.user_id
    order by o.created_at desc
    limit 5
    '''
    cursor.execute(sql)
    latest_orders = cursor.fetchall()
    
    #fetch latest users
    sql = '''select user_id, full_name, email, created_at
    from users order by created_at desc
    limit 5
    '''
    cursor.execute(sql)
    latest_users = cursor.fetchall()
    cursor.close()
    return render_template("admin_dashboard.html",total_products=total_products,
                           total_categories=total_categories,total_users=total_users,
                           total_orders=total_orders,latest_orders=latest_orders,
                           latest_users=latest_users)
    
    
   
#admin logout    
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id",None) 
    return redirect(url_for("login"))

#category management
#add category (admin only)
@app.route("/admin/add_category",methods=["GET","POST"])
def add_category():
    if "admin_id" not in session:
        return redirect(url_for(login))
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        f = request.files["imageurl"]
        
        filename = secure_filename(f.filename)
        filename = "static/images/"+f.filename
        #this will save the file to the specified location
        f.save(filename)
        filename = "images/"+f.filename 
        
        cursor = con.cursor(dictionary=True)
        sql = "insert into categories (name, description,image_url) values (%s ,%s, %s)"
        val = (name,description,filename)
        cursor.execute(sql,val)
        con.commit()
        return redirect(url_for("admin_dashboard"))
    else:
        return render_template("add_category.html") 
    
#view all categories (admin only)
@app.route("/admin/categories")
def view_categories():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    sql = "select * from categories"
    cursor.execute(sql)
    categories = cursor.fetchall()
    return render_template("view_categories.html",categories=categories)

#Edit category(admin only)
@app.route("/admin/edit_category/<category_id>",methods=["GET","POST"])
def edit_category(category_id):
    if "admin_id" not in session:
        return redirect(url_for('login'))
    
    cursor = con.cursor(dictionary=True)
    if request.method == "GET":
        sql = "select * from categories where category_id = %s"
        val = (category_id,)
        cursor.execute(sql,val) 
        category = cursor.fetchone()
        return render_template("edit_category.html",category=category)
    else:
        name = request.form["name"]
        description = request.form["description"]
        f = request.files["imageurl"]
        
        filename = secure_filename(f.filename)
        filename = "static/images/"+f.filename
        #this will save the file to the specified location
        f.save(filename)
        filename = "images/"+f.filename 
        
        sql = "update categories set name = %s, description = %s, image_url = %s where category_id = %s"
        val = (name,description,filename,category_id)
        cursor.execute(sql,val)
        con.commit()
        return redirect(url_for("view_categories"))
    
#delete category (admin_only)
@app.route("/admin/delete_category/<category_id>", methods=['GET','POST'])
def delete_category(category_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template("delete_category.html")
    else:
        action = request.form['action']
        if action == "Yes":
            cursor = con.cursor()
            sql = "Delete from categories where category_id = %s"
            val =(category_id,)
            cursor.execute(sql,val)
            con.commit()
        return redirect(url_for('view_categories'))
    
#product management..
#add product
@app.route("/admin/add_product",methods=["GET","POST"])
def add_products():
    cursor = con.cursor(dictionary=True)
    cursor.execute("select * from categories") 
    categories = cursor.fetchall()

    if "admin_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "GET":
        return render_template("add_product.html",categories=categories)
    else:
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]
        category_id = request.form["category_id"]
        rating = request.form["rating"]
        f = request.files["imageurl"]
        
        filename = secure_filename(f.filename)
        filename = "static/images/"+f.filename
        #this will save the file to the specified location
        f.save(filename)
        filename = "images/"+f.filename
        
        cursor = con.cursor(dictionary=True)
        sql = "insert into products(name,description,price,stock,category_id,image_url,rating) values (%s ,%s ,%s ,%s ,%s ,%s, %s)"
        val = (name,description,price,stock,category_id,filename,rating)
        cursor.execute(sql,val)
        con.commit()
        return redirect(url_for("view_products"))
   
# admin view products    
@app.route("/admin/products") 
def view_products():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    sql = "select * from products"
    cursor.execute(sql)
    products = cursor.fetchall()
    sql = "select * from categories"
    cursor.execute(sql)
    categories = cursor.fetchall()
    return render_template("view_products.html",products=products,categories=categories)

#admin edit products
@app.route("/admin/edit_product/<product_id>",methods = ["GET","POST"])
def edit_product(product_id):
    if "admin_id" not in session:
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    if request.method == "GET":
        sql = "select * from products where product_id = %s"
        val = (product_id,)
        cursor.execute(sql,val)
        product = cursor.fetchone()
        cursor.execute("select * from categories")
        categories = cursor.fetchall()
        return render_template("edit_product.html",product=product,categories=categories)
    else:
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        stock = request.form["stock"]
        category_id = request.form["category_id"]
        rating = request.form["rating"]
        f = request.files["imageurl"]
        
        filename = secure_filename(f.filename)
        filename = "static/images/"+f.filename
        #this will save the file to the specified location
        f.save(filename)
        filename = "images/"+f.filename
        
        cursor = con.cursor(dictionary=True)
        sql = "update products set name = %s, description = %s,price = %s,stock = %s,category_id = %s, image_url = %s, rating = %s where product_id = %s"
        val = (name,description,price,stock,category_id,filename,rating,product_id)
        cursor.execute(sql,val)
        con.commit()
        return redirect(url_for("view_products"))

#admin delete products
@app.route("/admin/delete_product/<product_id>",methods=["GET","POST"])
def delete_product(product_id):
    if "admin_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        action = request.form["action"]
        if action == "Yes":
            cursor = con.cursor()
            sql = "delete from products where product_id = %s"
            val = (product_id,)
            cursor.execute(sql,val)   
            con.commit()
        return redirect(url_for("view_products"))
    else:
        return render_template("delete_product.html",item_type = "product")        

    
#user profile update   
@app.route("/profile",methods=["GET","POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True) 
    sql = "select * from users where user_id = %s"
    val = (session['user_id'],)
    cursor.execute(sql,val)
    user = cursor.fetchone() 
    cursor.close()
    
    if request.method == "POST":
        # update user profile info
        full_name = request.form["full_name"] 
        address = request.form["address"] 
        city = request.form["city"]
        phone_number = request.form["phone_number"]
        
        cursor = con.cursor()
        sql = "update users set full_name = %s, address=%s, city=%s, phone_number=%s where user_id = %s"
        val = (full_name,address,city,phone_number,session["user_id"])
        cursor.execute(sql,val)
        con.commit()
        cursor.close()    
        return redirect("/profile") 

    return render_template("profile.html",user=user) 

#productlisting
@app.route("/category/<category_id>")
def product_listing(category_id):
    cursor = con.cursor(dictionary=True)
    sql = "select * from products where category_id = %s"
    val = (category_id,)
    cursor.execute(sql,val)
    products = cursor.fetchall()
    cursor.close()
    
    #fetch category name
    cursor = con.cursor(dictionary=True)
    sql = "select * from categories where category_id = %s"
    val = (category_id,)
    cursor.execute(sql,val)
    category = cursor.fetchone()
    cursor.close()
    return render_template("product_listing.html",products=products,category=category)

#product detail route
@app.route("/product/<product_id>")
def product_details(product_id):
    cursor = con.cursor(dictionary=True)
    sql = "select * from products where product_id = %s"
    val = (product_id,)
    cursor.execute(sql,val)
    product = cursor.fetchone()
    cursor.close()
    
    if not product:
        return "Product not found", 404
    
    return render_template("product_details.html",product=product)

#add to cart route
@app.route("/add_to_cart/<product_id>")
def add_to_cart(product_id):
    # get user_id from session
    user_id = session.get("user_id")
    if not user_id:
        flash("please log in to add items to your cart","error")
        return redirect(url_for("login"))
    
    # check if the product is already in the cart
    cursor = con.cursor(dictionary=True)
    sql = "select * from shopping_cart where user_id = %s and product_id = %s"
    val = (user_id,product_id)
    cursor.execute(sql,val)
    cart_item = cursor.fetchone()
    
    if cart_item:
        #update the quantity if the product is already in the cart
        new_quantity = cart_item["quantity"] + 1
        sql = "update shopping_cart set quantity = %s where cart_id = %s"
        cursor.execute(sql, (new_quantity, cart_item["cart_id"]))
    else:
        # insert the new item into cart
        sql = "insert into shopping_cart (user_id, product_id, quantity) values (%s, %s, %s)"
        cursor.execute(sql, (user_id, product_id, 1)) 
    con.commit()
    cursor.close()
    
    # fetch product name for the flash message
    cursor = con.cursor(dictionary=True)
    sql = "select name from products where product_id = %s"
    val = (product_id,)
    cursor.execute(sql,val)
    product = cursor.fetchone()
    flash(f"{product['name']} added to cart","success")
    
    return redirect(url_for("product_details",product_id=product_id))   
 
#view cart
@app.route("/cart")
def view_cart():
    user_id = session.get("user_id")
    if not user_id:
        flash("please log in to view your cart","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    sql = '''
        select sc.cart_id, sc.quantity, p.product_id, p.rating, p.name as product_name, p.price, p.image_url,p.description, c.name as category_name
        from shopping_cart sc
        join products p on sc.product_id = p.product_id
        join categories c on p.category_id = c.category_id
        where sc.user_id = %s
    ''' 
    cursor.execute(sql,(user_id,))
    cart_items = cursor.fetchall()
    cursor.close()
    
    #calculate total price 
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return render_template("cart.html",cart_items=cart_items, total_price = total_price)

@app.context_processor
def cart_count():
    if 'user_id' in session:
        user_id = session['user_id']
        sql = """
            SELECT 
                (select count(*) from shopping_cart where user_id = %s) as cart_count,
                (select count(*) from wishlists where user_id = %s) as wishlist_count
        """
        cursor = con.cursor()
        cursor.execute(sql, (user_id, user_id))
        result = cursor.fetchone()
        cart_item_count = result[0] if result and result[0] else 0
        wishlist_item_count = result[1] if result and result[1] else 0
        cursor.close()
    else:
        cart_item_count = 0
        wishlist_item_count = 0
    return {
        'cart_item_count': cart_item_count,
        'wishlist_item_count': wishlist_item_count
    }

# update quantity route 
@app.route("/update_cart/<cart_id>",methods = ["POST"])
def update_cart(cart_id):
    change = int(request.form.get("change", 0))
    cursor = con.cursor(dictionary=True)
    
    # Fetch current quantity
    sql = "select quantity from shopping_cart where cart_id = %s"
    cursor.execute(sql, (cart_id,))
    cart_item = cursor.fetchone()
    
    if cart_item:
        new_quantity = cart_item["quantity"] + change
        if new_quantity < 1:
            flash("Quantity cannot be less than 1. To remove the item, click the remove button.", "warning")
            cursor.close()
            return redirect(url_for("view_cart"))
        
        # Update the quantity in the database
        update_sql = "update shopping_cart set quantity = %s where cart_id = %s"
        cursor.execute(update_sql, (new_quantity, cart_id))
        con.commit()
        flash("Cart updated successfully.", "success")
    else:
        flash("Cart item not found.", "error")
    
    cursor.close()
    return redirect(url_for("view_cart"))

# remove item from route
@app.route("/remove_from_cart/<cart_id>")
def remove_from_cart(cart_id):
    cursor = con.cursor()
    sql = "delete from shopping_cart where cart_id = %s"
    cursor.execute(sql,(cart_id,))
    con.commit()
    cursor.close()
    
    flash("Item removed from cart.", "success")
    return redirect(url_for("view_cart"))
   
# add to wishlist route
@app.route("/wishlist/add/<product_id>")
def add_to_wishlist(product_id):
    # get user_id from session
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to add items to your wishlist.","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    
    # check if the product is already in the wishlist
    sql = "select * from wishlists where user_id = %s and product_id = %s"
    val = (user_id,product_id)
    cursor.execute(sql,val)
    wishlist_item = cursor.fetchone()
    
    if wishlist_item:
        flash("Product is already in your wishlist.","warning")
    else:
        # Insert the new item into wishlist
        sql = "insert into wishlists (user_id,product_id) values (%s,%s)"
        val = (user_id,product_id)
        cursor.execute(sql,val)
        con.commit()
        flash("Product added to your wishlist.","success")
        
    cursor.close()
    return redirect(url_for("product_details",product_id=product_id)) 

# view wishlist
@app.route("/wishlists")
def view_wishlist():
    user_id = session.get("user_id")
    if not user_id:
        flash("please log in to view your wishlist.","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    sql = '''
        select w.wishlist_id, p.product_id, p.name as product_name, p.description, p.price, p.image_url, p.rating, c.name as category_name
        from wishlists w
        join products p on w.product_id = p.product_id
        join categories c on p.category_id = c.category_id
        where w.user_id = %s
    '''       
    cursor.execute(sql, (user_id,))
    wishlist_items = cursor.fetchall()
    cursor.close()
    
    return render_template("wishlists.html",wishlist_items=wishlist_items)

# Remove from wishlist route
@app.route("/wishlist/remove/<wishlist_id>")
def remove_from_wishlist(wishlist_id):
    cursor = con.cursor()
    sql = "delete from wishlists where wishlist_id = %s"
    cursor.execute(sql,(wishlist_id,))
    con.commit()
    cursor.close()
    
    flash("Item removed from wishlist.","success")
    return redirect(url_for("view_wishlist"))
 
# buy now route
@app.route("/buy_now/<product_id>",methods=["GET","POST"])
def buy_now(product_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("please log in to proceed with the purchase.","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    #fetch product details
    sql = '''
        select p.product_id ,p.name, p.price, p.image_url, p.description,p.rating,c.category_id, c.name as category_name 
        from products p 
        join categories c on p.category_id = c.category_id
        where p.product_id = %s
    '''   
    cursor.execute(sql,(product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash("product not found.","error")
        return redirect(url_for("home"))
    cursor.close()
    
    #prepare data for checkout
    checkout_data = {
        'cart_items': [{
            'product_id': product['product_id'],
            'product_name': product['name'],
            'price': float(product['price']),
            'image_url': product['image_url'],
            'quantity': 1,
            'category_name': product['category_id'],
            'rating': product['rating']
        }],
        'total_amount': float(product['price']),
        'source': 'buy_now'
    }
    session['checkout_data'] = checkout_data
    return redirect(url_for("checkout"))

#proceed to checkout route from cart
@app.route("/proceed_to_checkout",methods=['GET'])
def proceed_to_checkout():
    user_id = session.get("user_id")
    if not user_id:
        flash("please log in to continue.","error") 
        return redirect(url_for('login'))
    
    cursor = con.cursor(dictionary=True)
    try:
        #fetch cart items for the user
        sql = '''
            select sc.cart_id, sc.quantity, p.product_id, p.name as product_name, p.price, p.image_url, p.rating, c.name as category_name
            from shopping_cart sc
            join products p on sc.product_id = p.product_id
            join categories c on p.category_id = c.category_id
            where sc.user_id = %s
        '''  
        cursor.execute(sql, (user_id,))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            flash("Your cart is empty.","warning")
            cursor.close()
            return redirect(url_for("view_cart"))
        
        # Convert price to float for each cart item
        for item in cart_items:
            try:
                item['price'] = float(item['price'])
            except (ValueError, TypeError):
                item['price'] = 0.0  # Default to 0.0 if conversion fails
                
        #calculate total amount
        total_amount = sum(float(item['price']) * item['quantity'] for item in cart_items)
        #store checkout data in session to be accessed in checkout page
        checkout_data = {
            'cart_items': cart_items,
            'total_amount': total_amount,
            'source': 'cart'
        }               
        session['checkout_data'] = checkout_data
        return redirect(url_for('checkout'))
    finally:
        cursor.close()

# checkout route
@app.route("/checkout",methods=["GET"])
def checkout():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to continue.","error")
        return redirect(url_for("login"))
    
    checkout_data = session.get("checkout_data")
    if not checkout_data:
        flash("No items to checkout.","warning")
        return redirect(url_for("home"))
    
    # fetch user details
    cursor = con.cursor(dictionary=True)
    try:
        # Fetch user details
        sql = "select full_name, email, address from users where user_id = %s"
        cursor.execute(sql, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("home"))
        
        return render_template(
            'checkout.html',
            user=user,
            cart_items=checkout_data['cart_items'],
            total_amount=checkout_data['total_amount']
        )   
    
    finally:
        cursor.close()   

#place order route
@app.route("/place_order",methods=["POST"])
def place_order():
    user_id = session.get("user_id")
    if not user_id:
        flash("please log in to place an order.","error")
        return redirect(url_for('login'))
    checkout_data = session.get("checkout_data")
    if not checkout_data:
        flash("No items to place an order.","warning")
        return redirect(url_for('home'))
    
    shipping_address = request.form.get("shipping_address")
    payment_method = request.form.get("payment_method")
    
    if not shipping_address or not payment_method:
        flash("Please provide all necessary details.","warning")
        return redirect(url_for("checkout"))
    
    conn = con
    cursor = conn.cursor()
    try:
        # insert into order table
        sql_order = '''
            insert into orders (user_id, total_amount, order_status, shipping_address) values (%s, %s, %s, %s)
        '''
        cursor.execute(sql_order, (user_id, checkout_data["total_amount"],'pending',shipping_address))
        order_id = cursor.lastrowid
        
        # Insert into order items table
        sql_order_item = '''
            insert into order_items (order_id, product_id, quantity, price) values (%s, %s, %s, %s)
        '''
        for item in checkout_data['cart_items']:
            cursor.execute(sql_order_item, (order_id, item['product_id'],item['quantity'],float(item['price'])))
        
        # insert into payments table
        sql_payment = '''
            insert into payments (order_id, amount, payment_status, payemnt_method) values (%s, %s, %s, %s)
        '''  
        val = (order_id,checkout_data['total_amount'],'pending',payment_method)  
        cursor.execute(sql_payment, val)
        
        # clear shopping cart if source is "cart"
        if checkout_data['source'] == 'cart':
            sql_clear_cart = "delete from shopping_cart where user_id = %s"
            cursor.execute(sql_clear_cart, (user_id,))
            
        conn.commit()    
        
        flash("order placed successfully!","success")
        session.pop('checkout_data',None) 
        return redirect(url_for("order_confirmation", order_id=order_id)) 
    
    except Exception as e:
        conn.rollback()
        flash("An error occured while placing your order. Please try again.","error")
        print(e)
        return redirect(url_for("checkout"))
    
    finally:
        cursor.close()          
        
# order confirmation route
@app.route('/order_confirmation/<order_id>', methods=['GET'])    
def order_confirmation(order_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your orders.", "error")
        return redirect(url_for('login'))
    cursor = con.cursor(dictionary=True)
    
    # fetch order details
    sql_order = """
        select o.order_id, o.user_id, o.total_amount, o.order_status, o.shipping_address, o.created_at, p.payment_status, p.payemnt_method 
        from orders o join payments p on o.order_id = p.order_id
        where o.order_id = %s and o.user_id = %s
    """
    cursor.execute(sql_order, (order_id, user_id))
    order = cursor.fetchone()
    
    if not order:
        flash("Order not found","error")
        cursor.close()
        return redirect(url_for('home'))
    
    # fetch order items
    sql_order_items = '''
        select oi.*,p.name as product_name, p.image_url from order_items oi
        join products p on oi.product_id = p.product_id where oi.order_id = %s
    '''
    cursor.execute(sql_order_items, (order_id,))
    order_items = cursor.fetchall()
    cursor.close()
    return render_template("order_confirmation.html",order=order, order_items=order_items)

#view order route
@app.route("/my_orders")
def my_order():
    user_id = session.get("user_id")
    if not user_id :
        flash("Please log in to view your orders.","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    try:
        sql = '''
        select o.order_id, o.total_amount, o.order_status, o.shipping_address, o.created_at, p.payemnt_method, p.payment_status
        from orders o join payments p on o.order_id = p.order_id
        where o.user_id = %s
        order by o.created_at desc
        '''
        cursor.execute(sql,(user_id,))
        orders = cursor.fetchall()
        
        return render_template("my_orders.html",orders=orders)
    finally:
        cursor.close()
        
# view single order details
@app.route("/order/<order_id>")
def view_order(order_id):
    user_id = session.get("user_id") 
    if not user_id:
        flash("Please log in to view your orders.", "error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    try:
        # fetch order details
        sql_order = '''
            select o.order_id, o.total_amount, o.order_status, o.shipping_address, o.created_at, p.payemnt_method, p.payment_status
            from orders o join payments p on o.order_id = p.order_id
            where o.order_id = %s and o.user_id = %s
        '''        
        
        cursor.execute(sql_order, (order_id,user_id))
        order = cursor.fetchone()
        
        if not order:
            flash("order not found.","error")
            return redirect(url_for("my_orders"))
        # fetch order items
        sql_order_items = '''
            select oi.order_item_id, oi.product_id, p.name as product_name, p.image_url, oi.quantity, oi.price
            from order_items oi join products p on oi.product_id = p.product_id
            where oi.order_id = %s
        '''
        cursor.execute(sql_order_items, (order_id,))
        order_items = cursor.fetchall()
        
        return render_template("view_order.html", order=order, order_items=order_items)
    finally:
        cursor.close()
        
#view all users (admin only)
@app.route("/admin/users")
def view_users():
    if "admin_id" not in session:
        flash("please log in as admin to access this page.","error")
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    cursor.execute("select * from users")
    users = cursor.fetchall()
    cursor.close()
    return render_template("view_users.html",users=users)

#edit user(admin only)
@app.route("/admin/edit_user/<user_id>",methods=["GET","POST"])
def edit_user(user_id):
    if "admin_id" not in session:
        flash("please log in as admin to access this page","error")
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    if request.method == "GET":
        cursor.execute("select * from users where user_id = %s",(user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            flash("user not found","error")
            return redirect(url_for("view_users"))
        return render_template("edit_user.html",user=user)
    else:
        #handle post request to update user details
        full_name = request.form["full_name"]
        email = request.form["email"]
        address = request.form["address"]
        city = request.form["city"]
        phone_number = request.form["phone_number"]
        
        sql = "update users set full_name = %s, email = %s, address = %s, city= %s,phone_number=%s where user_id = %s"
        val = (full_name,email,address,city,phone_number,user_id)
        
        cursor.execute(sql,val)
        con.commit()
        cursor.close()
        flash("user details updated successfully.","success")
        return redirect(url_for("view_users"))
    
#delete user(admin only)
@app.route("/admin/delete_user/<user_id>",methods=["GET","POST"])
def delete_user(user_id):
    if "admin_id" not in session:
        flash("please log in as admin to access this page.","error")
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    if request.method == "GET":
        cursor.execute("select * from users where user_id = %s",(user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            flash("user not found.","error")
            return redirect(url_for("view_users"))
        return render_template("delete_user.html",user=user)
    else:
        action = request.form["action"]
        if action == "Yes":
            cursor.execute("delete from users where user_id = %s",(user_id,))
            con.commit()
            cursor.close()
            flash("user deleted successfully.","success")
        else:
            flash("user deletion canceled.","info")
            
        return redirect(url_for("view_users"))
    
# view all orders(admin only)
@app.route("/admin/orders")
def admin_view_orders():
    if "admin_id" not in session:
        flash("please log in as admin to access this page.","error")
        return redirect(url_for("login"))
    cursor = con.cursor(dictionary=True)
    sql = '''select o.order_id,o.user_id,u.full_name,o.total_amount,o.order_status,o.shipping_address,o.created_at
    from orders o join users u on o.user_id = u.user_id
    order by o.created_at desc
    '''
    cursor.execute(sql) 
    orders = cursor.fetchall()    
    cursor.close()
    return render_template("admin_view_orders.html",orders=orders)

#view order details (admin only)
@app.route("/admin/order/<order_id>")
def order_details(order_id):
    if "admin_id" not in session:
        flash("please log in as admin to access this page.","error") 
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    #fetch order details
    sql = '''select o.order_id,o.user_id,u.full_name,u.email,o.total_amount,o.order_status,o.shipping_address,o.created_at
    from orders o join users u on o.user_id = u.user_id where o.order_id = %s'''   
    val = (order_id,)
    cursor.execute(sql,val)
    order = cursor.fetchone()
    if not order:
        flash("order not found.","error")
        cursor.close()
        return redirect(url_for("admin_view_orders"))
    #fetch order items
    order_item_sql = ''' select oi.order_item_id, oi.product_id,p.name as product_name,p.image_url,oi.quantity,oi.price
    from order_items oi
    join products p on oi.product_id = p.product_id
    where oi.order_id = %s'''
    val = (order_id,)
    cursor.execute(order_item_sql,val)
    order_items = cursor.fetchall()
    # fetch payment details
    cursor.execute("select * from payments where order_id = %s",(order_id,))
    payment = cursor.fetchone()
    cursor.close()
    return render_template("admin_order_details.html",order=order,order_items=order_items,payment=payment)

# update order status (admin only)
@app.route("/update_order_status/<order_id>",methods=["GET","POST"])
def update_order_status(order_id):
    if "admin_id" not in session:
        flash("please log in as admin to access this page","error")
        return redirect(url_for("login"))
    
    cursor = con.cursor(dictionary=True)
    
    if request.method == "GET":
        cursor.execute("select order_status from orders where order_id = %s",(order_id,))
        order = cursor.fetchone()
        
        if not order:
            flash("order not found.","error")
            cursor.close()
            return redirect(url_for("admin_view_orders"))
        
        return render_template("admin_update_order_status.html",current_status=order["order_status"], order_id=order_id)
    else:
        new_status = request.form["order_status"]
        sql = "update orders set order_status = %s where order_id = %s"
        cursor.execute(sql,(new_status,order_id))
        con.commit()
        cursor.close()
        
        flash("order status updated successfully.","success")
        return redirect(url_for("admin_view_orders"))

        
if __name__ == "__main__":
    app.run(debug=True)