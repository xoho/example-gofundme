from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    wait_time = between(0.5, 3)

    @task(3)
    def index_page(self):
        self.client.get("/")

    @task(1)
    def login_page(self):
        self.client.get("/login")

    @task(1)
    def search(self):
        self.client.get("/search")

    @task(1)
    def logout(self):
        self.client.get("/logout")

    @task(12)
    def page0(self):
        self.client.get(
            "https://myfundquest.com/campaign/IjQ5szbwZSRLoaQTr5ivRFmdWAm79E13"
        )
