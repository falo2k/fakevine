# ruff: noqa: S311
import random

from locust import HttpUser, task


class LocusTests(HttpUser):

    @task
    def get_volumes(self):
        volume_searchkeys = ['', 'batman', 'catwoman', 'invincible', 'iron', 'the boys', 'duck tales']

        searchkey = random.choice(volume_searchkeys)

        if searchkey == '':
            self.client.get("/volumes?api_key=12345&format=json")
        else:
            self.client.get(f"/volumes?api_key=12345&format=json&filter=name:{searchkey}")


    def get_volume(self):
        volume_ids: list[str] = ['111970', '55260', '10813', '113467', '332134']

        vol_id = random.choice(volume_ids)

        self.client.get(f"/volume/4000-{vol_id}?api_key=12345&format=json")



    @task
    def get_people(self):
        self.client.get("/people?api_key=12345&format=json")


    @task
    def get_types(self):
        self.client.get("/types?api_key=12345&format=json")
