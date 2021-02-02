# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest 

from run import app

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_app_smoke(self):
        # Check status codes
        result = self.app.get('/')
        self.assertEqual(result.status_code, 200)

        result = self.app.get('/optimization')
        self.assertEqual(result.status_code, 200)

        # Check that map was saved
        map_file = 'templates/map.html'
        self.assertTrue(os.path.isfile(map_file))
        os.remove(map_file)

if __name__ == '__main__':
    unittest.main()
