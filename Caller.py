import requests

BASE_URL = "http://127.0.0.1:8000"

TEST_USER = {
    "username": "testuser",
    "full_name": "Test User",
    "email": "testuser@example.com",
    "password": "TestPassword123!"
}


def register():
    url = f"{BASE_URL}/register"
    r = requests.post(url, json=TEST_USER)
    print("REGISTER:", r.status_code, r.text)


def login():
    url = f"{BASE_URL}/token"

    data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    }

    r = requests.post(url, data=data)

    print("LOGIN:", r.status_code)

    if r.status_code != 200:
        print(r.text)
        return None

    token = r.json()["access_token"]
    return token


def create_project(token):
    url = f"{BASE_URL}/project/new"
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "name": "mi_proyecto"
    }

    r = requests.post(url, headers=headers, data=data)

    print("CREATE PROJECT:", r.status_code, r.text)


def check_project(token):
    url = f"{BASE_URL}/project/check"

    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "name": "mi_proyecto"
    }

    r = requests.get(url, headers=headers, params=params)

    print("CHECK PROJECT:", r.status_code, r.text)


def upload_file(token):
    url = f"{BASE_URL}/upload-doc"
    headers = {"Authorization": f"Bearer {token}"}

    files = {
        "file": ("smowl.pdf", open("doc.pdf", "rb"))
    }

    data = {
        "name": "mi_proyecto",
        "file_type": "pdf"
    }

    r = requests.post(url, headers=headers, files=files, data=data)

    print("UPLOAD FILE:", r.status_code, r.text)


def RAG_project(token):
    url = f"{BASE_URL}/project/compile"

    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "name": "mi_proyecto"
    }

    r = requests.get(url, headers=headers, params=params)

    print("COMPILE PROJECT:", r.status_code, r.text)


def create_collection(token, collectionname="TEST"):
    url = f"{BASE_URL}/collections/{collectionname}/create"
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.post(url, headers=headers)

    print("CREATE ASPECT:", r.status_code, r.text)


def add_question(token, collectionname, question):
    url = f"{BASE_URL}/collections/{collectionname}/add-question"
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "question": question
    }

    r = requests.post(url, headers=headers, data=data)

    print("ADD QUESTION:", r.status_code, r.text)


def get_question_id(token, collectionname, question):
    url = f"{BASE_URL}/collections/{collectionname}/question-id"
    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "question": question
    }

    r = requests.get(url, headers=headers, params=params)

    print("GET QUESTION ID:", r.status_code, r.text)

    if r.status_code == 200:
        return r.json().get("id", -1)

    return -1


def modify_question(token, collectionname, question, new_question):
    url = f"{BASE_URL}/collections/{collectionname}/modify-question"
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "question": question,
        "new_question": new_question
    }

    r = requests.put(url, headers=headers, data=data)

    print("MODIFY QUESTION:", r.status_code, r.text)


def delete_question(token, collectionname, question):
    url = f"{BASE_URL}/collections/{collectionname}/delete-question"
    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "question": question
    }

    r = requests.delete(url, headers=headers, params=params)

    print("DELETE QUESTION:", r.status_code, r.text)
    

def ExecuteCollections(token):
    url = f"{BASE_URL}/project/excecute"

    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "name": "mi_proyecto"
    }

    r = requests.get(url, headers=headers, params=params)

    print("EXECUTED PROJECT:", r.status_code, r.text)


if __name__ == "__main__":
    register()
    token = login()
    
    if token:
        create_project(token)
        check_project(token)
        upload_file(token)
        RAG_project(token)

        # Create a new collection called "TEST"
        create_collection(token, "TEST")

        # Upload questions
        q1 = "el proyecto califica o toma decisiones"
        q2 = "se usan datos de caracter identificativo como nombre, NIF, DNI, telefono o email"
        q3 = "¿?"

        add_question(token, "TEST", q1)
        add_question(token, "TEST", q2)
        add_question(token, "TEST", q3)

        # Modify "¿?" to "¿-?"
        modify_question(token, "TEST", q3, "¿-?")

        # Delete "¿-?"
        delete_question(token, "TEST", "¿-?")
        
        # Launch all queries.
        ExecuteCollections(token)
        

