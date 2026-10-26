# 群聊开关 (astrbot_plugin_group_chat_switch)

用一句话在聊天框里开关某个群的 AI 聊天，不用开 WebUI。

AstrBot 本身已经支持**会话级** LLM 开关（面板 → 会话管理 → 该会话 → LLM 开关），
但入口只在管理面板里。人在外面、只有手机、刚把机器人拉进一个新群时，那条路走不通。

这个插件把同一个字段的写入搬到聊天框：写的是官方配置
（`session_service_config.llm_enabled`，按会话隔离），
所以与面板完全同源 —— 两边谁改都生效，不会互相覆盖。

## 指令

| 指令 | 作用 |
| --- | --- |
| `/开聊` | 在当前会话打开 LLM 聊天 |
| `/关聊` | 在当前会话关闭 LLM 聊天（指令仍可用） |
| `/聊状态` | 查看当前会话的开关与来源 |
| `/开聊 123456789` | 按群号远程打开（私聊里也能用） |
| `/关聊 123456789` | 按群号远程关闭 |
| `/chat on\|off\|status [群号]` | 英文别名 |

权限：仅 AstrBot 管理员（`admins_id`）可执行，群内的群主/管理员无效。

## 行为说明

- 关闭后，LLM 请求在 `agent_request` 阶段直接返回，**指令仍然照常执行**；
- 修改立即生效，不需要重载插件、也不需要重启 AstrBot；
- 未设置过的会话默认「开」，即 `llm_enabled` 未写入时按 AstrBot 原有默认行为；
- 本插件不注册任何「通吃所有消息」的处理器，因此不会影响唤醒逻辑。

## 安装

```bash
cd AstrBot/data/plugins
git clone <本仓库地址>
```

然后在 WebUI 的插件页重载，或重启 AstrBot。

## 兼容性

- AstrBot >= 4.20（依赖 `SessionServiceManager.set_llm_status_for_session`）
- 平台无关：aiocqhttp / qq_official / telegram / discord / webchat 均可；
  远程按群号开关只在有「群号」概念的平台上有效。

## 注意

- 这是**按会话**的开关，不是「新群默认闭嘴」。若需要后者，必须注册全量消息处理器，
  那会导致机器人在每个群都被唤醒，属于设计取舍，本项目不做。
- 关闭的是 AI 对话能力，不是整个机器人：其他插件的指令不受影响。

## License

MIT
