from locust import HttpUser, task, between
import os

# Load from environment variable — never hardcode tokens
TEST_JWT = os.getenv("TEST_JWT", "")

class JobFitUser(HttpUser):
    wait_time = between(1, 3)

    headers = {"Authorization": f"Bearer {TEST_JWT}"}

    @task(1)
    def health_check(self):
        self.client.get("/")

    @task(3)
    def search_jobs(self):
        self.client.get(
            "/jobs",
            params={"role": "GenAI Engineer", "location": "India"},
            headers=self.headers
        )

    @task(1)
    def match_jobs(self):
        sample_jobs = [
            {
                "title": "GenAI Engineer",
                "company": "Test Corp",
                "location": "Bangalore",
                "description": "Looking for GenAI Engineer with Python LangChain RAG experience",
                "url": "https://example.com",
                "source": "jsearch"
            }
        ] * 3

        self.client.post(
            "/match",
            json={"jobs": sample_jobs},
            headers=self.headers,
            timeout=120
        )
