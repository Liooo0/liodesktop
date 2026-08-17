# Changelog

## [Unreleased]

### Fixed

- **死锁**: `ConfigManager.set()/update_deepseek()` 持锁后再次 `save()` 抢同一把非重入锁导致死锁,拆出 `_save_locked()`(锁由调用方持有)
- `app.py` 清理历史死代码:`start_kernel()`/`READY` 事件/无意义的 `PORT = 0` 全局变量

### Changed

- **配置系统**: 浅 `dict.update` 改为递归 `deep_merge`——用户只配 `deepseek.api_key` 时,`base_url` 等嵌套默认值不再被整体覆盖;新增 `config_version` 字段与 `update_deepseek()` 专用入口
- **错误体系**: 新增 `core/errors.py`(`AppError` 层次: Auth/Network/RateLimit/Provider/Validation),API 统一返回 `{code, message}`,真实异常进日志不泄漏给前端;适配层 `auth:/limit:/network:/service:` 前缀异常自动映射错误码
- 路由错误处理统一走 `to_error_response`,删除裸 `str(e)` 外泄

### Added

- 测试: `test_config.py`(deep_merge/权限600/损坏文件兜底) + `test_service_manager.py`(状态机) + `test_errors.py`(错误码映射),共 19 个用例
- GitHub Actions CI(pytest + ruff)