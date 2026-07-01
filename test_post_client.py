import json
import urllib.request
import urllib.error

def test_post():
    login_url = "http://127.0.0.1:8000/api/auth/login"
    login_payload = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("Logging in...")
    try:
        req = urllib.request.Request(
            login_url,
            data=json.dumps(login_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            login_res = json.loads(res.read().decode("utf-8"))
            print("Login success!")
    except urllib.error.HTTPError as e:
        print("Login failed! Status:", e.code)
        print("Response:", e.read().decode("utf-8"))
        return
    except Exception as e:
        print("Error logging in:", e)
        return
        
    token = login_res["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    product_payload = {
        "name": "Test Cake Client API",
        "short_description": "A delicious test cake from client.",
        "full_description": "This is a full description of the test cake.",
        "category_id": None,
        "cake_type": "Cream Cake",
        "flavor": "Chocolate",
        "shape": "Round",
        "weight_options": '["500g", "1kg"]',
        "original_price": 499.0,
        "selling_price": 499.0,
        "discount_percent": 0.0,
        "preparation_time": "24 hours",
        "serves": "6-8 people",
        "ingredients": "chocolate, flour, sugar",
        "storage_instructions": "refrigerator",
        "is_customizable": False,
        "is_available": True,
        "is_best_seller": False,
        "is_trending": False,
        "is_new_arrival": True,
        "is_eggless": True
    }
    
    print("Posting product...")
    try:
        req_prod = urllib.request.Request(
            "http://127.0.0.1:8000/api/products/",
            data=json.dumps(product_payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req_prod) as res_prod:
            print("Product success! Status:", res_prod.status)
            print("Response:", res_prod.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("Product failed! Status:", e.code)
        print("Response:", e.read().decode("utf-8"))
    except Exception as e:
        print("Error posting product:", e)

if __name__ == "__main__":
    test_post()
