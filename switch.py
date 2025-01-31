import logging
import voluptuous as vol
from homeassistant.components.switch import (
    SwitchEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv

import socket
import json
import time

_LOGGER = logging.getLogger(__name__)

# 目标设备的 IP 地址和端口
TARGET_IP = "192.168.31.161"
TARGET_PORT = 11315

CONF_USR_DATA_SN = "usr_data_sn"
CONF_PHONE_NUM = "phone_num"
CONF_DESTINATION_ID = "destination_id"
CONF_SOURCE_ID = "source_id"


SwitchIDMap = {
    "living_room_chandelier": "00090A01010101",
    "living_room_spot_light": "00090701010102",
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_USR_DATA_SN): cv.string,
        vol.Required(CONF_PHONE_NUM): cv.string,
        vol.Required(CONF_DESTINATION_ID): cv.string,
        vol.Required(CONF_SOURCE_ID): cv.string,
    }
)


def send_command(command):
    """发送命令到目标设备并接收响应"""
    try:
        # 创建 TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 连接到目标设备
        client_socket.connect((TARGET_IP, TARGET_PORT))

        # 将命令转换为 JSON 字符串并发送
        json_command = json.dumps(command)
        client_socket.sendall(json_command.encode())

        # 接收响应
        response = client_socket.recv(4096)
        if response:
            try:
                json_response = json.loads(response.decode())
                _LOGGER.debug("接收到响应: %s", json_response)
                return json_response
            except json.JSONDecodeError:
                _LOGGER.warning("接收到非JSON响应: %s", response.decode())
                return response.decode()
        else:
            _LOGGER.warning("未接收到响应")
            return None

    except Exception as e:
        _LOGGER.error("发生错误: %s", e)
        return None
    finally:
        # 关闭连接
        client_socket.close()


class LightSwitch(SwitchEntity):
    # 设备状态
    class Action:
        OPEN = "open"
        CLOSE = "close"

    def __init__(self, name,):
        """初始化开关."""
        self._name = name
        self._device_id = SwitchIDMap[name]
        self._usr_data_sn = "1738310883024"
        self._phone_num = "13652388"
        self._destination_id = "0A010101"
        self._source_id = "00fefc"
        self._state = False  # 初始状态为关闭

    @property
    def name(self):
        """返回开关的名称."""
        return self._name

    @property
    def is_on(self):
        """如果开关打开，则返回 True."""
        return self._state

    def control_device(self, action: Action):
        """发送打开设备的命令"""
        command = {
            "Command": [
                {
                    "ccmdId": self._device_id,
                    "cmd": [{"action": action}],
                    "destinationId": self._destination_id,
                    "sourceId": self._source_id,
                }
            ],
            "UsrDataSN": self._usr_data_sn,
            "phoneNum": self._phone_num,
        }
        return send_command(command)

    def get_device_status(self):
        """发送获取设备状态的命令"""
        command = {
            "UsrDataSN": self._usr_data_sn,
            "command": "get_status",
        }  # 假设的命令
        return send_command(command)

    def turn_on(self, **kwargs):
        """打开开关."""
        _LOGGER.debug("打开设备...")
        action = LightSwitch.Action.OPEN
        action_response = self.control_device(action)
        if action_response:
            _LOGGER.debug("设备命令发送成功")
            time.sleep(1)  # 等待设备响应

            # 获取设备状态
            _LOGGER.debug("发送获取设备状态命令...")
            status_response = self.get_device_status()
            if status_response:
                _LOGGER.debug("设备状态获取成功")
                self._state = True
                self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """关闭开关."""
        _LOGGER.debug("关闭设备...")
        action = LightSwitch.Action.CLOSE
        action_response = self.control_device(action)
        if action_response:
            _LOGGER.debug("设备命令发送成功")
            time.sleep(1)  # 等待设备响应

            # 获取设备状态
            _LOGGER.debug("发送获取设备状态命令...")
            status_response = self.get_device_status()
            if status_response:
                _LOGGER.debug("设备状态获取成功")
                self._state = False
                self.schedule_update_ha_state()


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """设置开关平台."""
    name = config.get(CONF_NAME)

    dev = LightSwitch(name)
    async_add_entities([dev])
    