#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 指定解释器为 python3，并设置文件编码为 UTF-8

import celery  # 导入 Celery 库，用于处理异步任务
import celery_aio_pool  # 导入 celery_aio_pool 库，用于支持异步任务池

from backend.app.task.conf import task_settings  # 从项目配置中导入任务相关的设置
from backend.core.conf import settings  # 从项目配置中导入全局设置

__all__ = ['celery_app']  # 定义模块的公共接口，仅暴露 celery_app 实例


def init_celery() -> celery.Celery:
    """初始化 celery 应用"""

    # TODO: 如果 Celery 版本 >= 6.0.0，需要更新这部分代码
    # 相关 issue 链接：
    # https://github.com/fastapi-practices/fastapi_best_architecture/issues/321
    # https://github.com/celery/celery/issues/7874
    celery.app.trace.build_tracer = celery_aio_pool.build_async_tracer  # 替换 Celery 的默认 tracer 为异步 tracer
    celery.app.trace.reset_worker_optimizations()  # 重置 worker 的优化设置

    # Celery 定时任务配置
    # 参考文档：https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
    beat_schedule = task_settings.CELERY_SCHEDULE  # 从配置中获取定时任务计划

    # Celery 配置
    # 参考文档：https://docs.celeryq.dev/en/stable/userguide/configuration.html
    # 根据配置选择 broker_url（消息队列的 URL）
    broker_url = (
        (
            f'redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:'
            f'{settings.REDIS_PORT}/{task_settings.CELERY_BROKER_REDIS_DATABASE}'
        )
        if task_settings.CELERY_BROKER == 'redis'  # 如果使用 Redis 作为 broker
        else (
            f'amqp://{task_settings.RABBITMQ_USERNAME}:{task_settings.RABBITMQ_PASSWORD}@'
            f'{task_settings.RABBITMQ_HOST}:{task_settings.RABBITMQ_PORT}'
        )  # 如果使用 RabbitMQ 作为 broker
    )
    # 配置 result_backend（任务结果存储的 URL）
    result_backend = (
        f'redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:'
        f'{settings.REDIS_PORT}/{task_settings.CELERY_BACKEND_REDIS_DATABASE}'
    )
    # 配置 result_backend_transport_options（任务结果存储的传输选项）
    result_backend_transport_options = {
        'global_keyprefix': f'{task_settings.CELERY_BACKEND_REDIS_PREFIX}',  # Redis 键前缀
        'retry_policy': {
            'timeout': task_settings.CELERY_BACKEND_REDIS_TIMEOUT,  # 超时重试策略
        },
    }

    # 创建 Celery 应用实例
    app = celery.Celery(
        'fba_celery',  # 应用名称
        enable_utc=False,  # 禁用 UTC 时间
        timezone=settings.DATETIME_TIMEZONE,  # 设置时区
        beat_schedule=beat_schedule,  # 设置定时任务计划
        broker_url=broker_url,  # 设置 broker URL
        broker_connection_retry_on_startup=True,  # 启动时重试 broker 连接
        result_backend=result_backend,  # 设置结果存储后端
        result_backend_transport_options=result_backend_transport_options,  # 设置结果存储传输选项
        task_cls='app.task.celery_task.base:TaskBase',  # 设置任务基类
        task_track_started=True,  # 启用任务启动跟踪
    )

    # 自动发现任务模块
    app.autodiscover_tasks(task_settings.CELERY_TASK_PACKAGES)

    return app  # 返回初始化后的 Celery 应用实例


# 创建 celery 实例
celery_app: celery.Celery = init_celery()
