from locust import HttpUser, task, between
import json

# A real JWT token from your browser session
# Get this from: browser → F12 → Application → Session Storage
TEST_JWT = "eyJhbGciOiJFUzI1NiIsImtpZCI6ImY5YjUwNTA4LTc3MDMtNDliZi1iN2E0LTJlYzY3YjExNDI0MyIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2R3cnl5Zm9raXNzbXpyaGFoZnJuLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIwYjBkM2JmYi0wZDg2LTQ5MjItOTlkZC0xNTkxYjdiMTMzNzIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgxNjQ5MjA2LCJpYXQiOjE3ODE2NDU2MDYsImVtYWlsIjoiZGVlcGFuamFsaXlhZGF2MjgzQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJkZWVwYW5qYWxpeWFkYXYyODNAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiMGIwZDNiZmItMGQ4Ni00OTIyLTk5ZGQtMTU5MWI3YjEzMzcyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3ODE2NDU2MDZ9XSwic2Vzc2lvbl9pZCI6IjYzYzg3NGNjLTFkZDMtNGE4ZC1iMWVlLTM4ZmRiMDk5ZWY5OSIsImlzX2Fub255bW91cyI6ZmFsc2V9.ZedswFjXFS54YQKwDBHEMjDcTNPNuv2IteaDtc-sZJ7lE-VbmxLDGlSPlT-WKqlU0XJoUNwXFj7dmpC-W_WVgg"

class JobFitUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    headers = {"Authorization": f"Bearer {TEST_JWT}"}

    @task(1)
    def health_check(self):
        """Lightest endpoint — just checks server is alive."""
        self.client.get("/")

    @task(3)
    def search_jobs(self):
        """Most common action — benefits from cache."""
        self.client.get(
            "/jobs",
            params={"role": "GenAI Engineer", "location": "India"},
            headers=self.headers
        )

    @task(1)
    def match_jobs(self):
        """Heaviest endpoint — calls Gemini 10 times."""
        # Use cached jobs so we don't waste JSearch quota
        sample_jobs = [
            {
                "title": "GenAI Engineer",
                "company": "Test Corp",
                "location": "Bangalore",
                "description": "Looking for GenAI Engineer with Python LangChain RAG experience",
                "url": "https://example.com",
                "source": "jsearch"
            }
        ] * 3  # 3 sample jobs to keep test fast

        self.client.post(
            "/match",
            json={"jobs": sample_jobs},
            headers=self.headers,
            timeout=120
        )