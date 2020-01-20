import os
import unittest

from mock import MagicMock

from cli.internal.apis.mason import MasonApi
from cli.internal.models.apk import Apk
from cli.internal.models.media import Media
from cli.internal.models.os_config import OSConfig
from tests import __tests_root__


class MasonApiTest(unittest.TestCase):
    def setUp(self):
        mock_handler = MagicMock()
        mock_auth_store = MagicMock()
        mock_auth_store.__getitem__ = MagicMock(return_value='Foobar')
        mock_endpoints_store = MagicMock()
        mock_endpoints_store.__getitem__ = MagicMock(return_value='url_root')

        self.handler = mock_handler
        self.api = MasonApi(mock_handler, mock_auth_store, mock_endpoints_store)
        self.api._customer = 'mason-test'

    def test__upload_artifact__config_requests_are_correct(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        artifact = OSConfig.parse(MagicMock(), config_file)
        self.handler.get = MagicMock(return_value={
            'signed_request': 'signed_request',
            'url': 'signed_url'
        })

        self.api.upload_artifact(config_file, artifact)

        self.handler.get.assert_called_with(
            'url_root/mason-test/project-id/1?type=config',
            headers={
                'Content-Type': 'application/json',
                'Content-MD5': 'BtYkQIi96WeIVrTFcPaYtQ==',
                'Authorization': 'Bearer Foobar'
            }
        )
        self.handler.put.assert_called_with(
            'signed_request',
            config_file,
            headers={'Content-Type': 'text/x-yaml', 'Content-MD5': 'BtYkQIi96WeIVrTFcPaYtQ=='}
        )
        self.handler.post.assert_called_with(
            'url_root/mason-test',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'},
            json={
                'name': 'project-id',
                'version': '1',
                'customer': 'mason-test',
                'url': 'signed_url',
                'type': 'config',
                'checksum': {'sha1': '1061ecf0b0a7269c352439e5f7c0819b268d8e6f'}
            }
        )

    def test__upload_artifact__apk_requests_are_correct(self):
        apk_file = os.path.join(__tests_root__, 'res/v1.apk')
        artifact = Apk.parse(MagicMock(), apk_file)
        self.handler.get = MagicMock(return_value={
            'signed_request': 'signed_request',
            'url': 'signed_url'
        })

        self.api.upload_artifact(apk_file, artifact)

        self.handler.get.assert_called_with(
            'url_root/mason-test/com.example.unittestapp1/1?type=apk',
            headers={
                'Content-Type': 'application/json',
                'Content-MD5': 'UK70RLRMCuewDJThkBcO8g==',
                'Authorization': 'Bearer Foobar'
            }
        )
        self.handler.put.assert_called_with(
            'signed_request',
            apk_file,
            headers={
                'Content-Type': 'application/vnd.android.package-archive',
                'Content-MD5': 'UK70RLRMCuewDJThkBcO8g=='
            }
        )
        self.handler.post.assert_called_with(
            'url_root/mason-test',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'},
            json={
                'name': 'com.example.unittestapp1',
                'version': '1',
                'customer': 'mason-test',
                'url': 'signed_url',
                'type': 'apk',
                'checksum': {'sha1': '9d66f37de677405cda3d01a3fab74879f816a65e'},
                'apk': {
                    'versionName': '1.0',
                    'versionCode': '1',
                    'packageName': 'com.example.unittestapp1'
                }
            }
        )

    def test__upload_artifact__media_requests_are_correct(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        artifact = Media.parse(MagicMock(), 'Boot Anim', 'bootanimation', '1', media_file)
        self.handler.get = MagicMock(return_value={
            'signed_request': 'signed_request',
            'url': 'signed_url'
        })

        self.api.upload_artifact(media_file, artifact)

        self.handler.get.assert_called_with(
            'url_root/mason-test/Boot Anim/1?type=media',
            headers={
                'Content-Type': 'application/json',
                'Content-MD5': 'HzF5jT1tn8nOtt33IcFWaQ==',
                'Authorization': 'Bearer Foobar'
            }
        )
        self.handler.put.assert_called_with(
            'signed_request',
            media_file,
            headers={'Content-Type': 'application/zip', 'Content-MD5': 'HzF5jT1tn8nOtt33IcFWaQ=='}
        )
        self.handler.post.assert_called_with(
            'url_root/mason-test',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'},
            json={
                'name': 'Boot Anim',
                'version': '1',
                'customer': 'mason-test',
                'url': 'signed_url',
                'type': 'media',
                'checksum': {'sha1': 'e7788dca3a3797fd152825e600047e7cef870d98'},
                'media': {'type': 'bootanimation'}
            }
        )

    def test__deploy_artifact__default_requests_are_correct(self):
        self.api.deploy_artifact('myType', 'myName', 'myVersion', 'myGroup', 'myPush', 'myNoHttps')

        self.handler.post.assert_called_with(
            'url_root',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'},
            json={
                'customer': 'mason-test',
                'group': 'myGroup',
                'name': 'myName',
                'version': 'myVersion',
                'type': 'myType',
                'push': True,
                'deployInsecure': True
            }
        )

    def test__start_build__default_requests_are_correct(self):
        self.api.start_build('project-id', 'myVersion', 'myFastBuild', None)

        self.handler.post.assert_called_with(
            'url_root/mason-test/jobs',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'},
            json={
                'customer': 'mason-test',
                'project': 'project-id',
                'version': 'myVersion',
                'fastBuild': True,
                'masonVersion': None
            }
        )

    def test__get_build__default_requests_are_correct(self):
        self.api.get_build('id')

        self.handler.get.assert_called_with(
            'url_root/mason-test/jobs/id',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer Foobar'}
        )
