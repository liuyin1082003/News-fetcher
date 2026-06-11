#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理管理器 — 多代理自动回退，确保国内网络能访问国外新闻源。

设计原则：
  - 仅在脚本进程内生效（通过 install_opener），不影响系统全局网络设置
  - 多级回退：手动配置 → 环境变量 → 免费代理池 → 直连
  - feedparser 底层使用 urllib.request.urlopen()，会自动走安装的 opener

用法：
  from proxy_manager import ProxyManager
  pm = ProxyManager()
  if pm.config["enabled"]:
      pm.install()
"""

import urllib.request
import urllib.error
import json
import os
import sys
import socket
import ssl
from datetime import datetime

# ─── Windows UTF-8 编码修复 ─────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ProxyManager:
    """代理管理器，负责代理发现、测试和安装"""

    # 用于测试代理连通性的目标站点列表（选稳定的国际站点）
    TEST_URLS = [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip",
        "http://rss.cnn.com/rss/edition.rss",
        "https://www.google.com/",
    ]

    # 免费代理 GitHub 列表（备用）
    FREE_PROXY_LISTS = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    ]

    def __init__(self, config_path=None):
        """初始化代理管理器

        Args:
            config_path: proxy_config.json 的路径，默认为同目录下的 proxy_config.json
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "proxy_config.json")
        self.config = self._load_config(config_path)
        self.current_proxy = None
        self._original_opener = None

    # ─── 配置加载 ────────────────────────────────────────────

    def _load_config(self, path):
        """加载代理配置文件，若文件不存在则使用默认配置"""
        default = {
            "enabled": False,
            "manual_proxies": [],
            "auto_fetch_free_proxies": False,
            "timeout": 15,
            "retry_count": 2,
        }
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                default.update(user_config)
        except FileNotFoundError:
            pass
        return default

    # ─── 代理发现 ────────────────────────────────────────────

    def discover_proxies(self):
        """按优先级收集所有可能的代理地址

        优先级：手动配置 > 环境变量 > 免费代理池

        Returns:
            list[str]: 代理 URL 列表
        """
        proxies = []

        # 1️⃣ 手动配置的代理（最高优先级）
        for p in self.config.get("manual_proxies", []):
            url = p.get("url", "")
            if url and url not in proxies:
                proxies.append(url)

        # 2️⃣ 系统环境变量中的代理
        for env_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"]:
            val = os.environ.get(env_var)
            if val and val not in proxies:
                proxies.append(val)

        # 3️⃣ 免费代理池（从 GitHub 获取）
        if self.config.get("auto_fetch_free_proxies", False) and not proxies:
            free = self._fetch_free_proxies()
            for p in free:
                if p not in proxies:
                    proxies.append(p)

        return proxies

    def _fetch_free_proxies(self):
        """从 GitHub 公共代理列表获取免费代理

        Returns:
            list[str]: 代理 URL 列表
        """
        proxies = []
        for list_url in self.FREE_PROXY_LISTS:
            try:
                req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode("utf-8")
                    for line in text.strip().split("\n"):
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
                if proxies:
                    break
            except Exception:
                continue
        print(f"📋 从免费代理池获取到 {len(proxies)} 个代理", file=sys.stderr)
        return proxies[:20]  # 最多取20个

    # ─── 代理测试 ────────────────────────────────────────────

    def test_proxy(self, proxy_url):
        """测试代理是否可用

        Args:
            proxy_url: 代理地址，如 http://127.0.0.1:7890

        Returns:
            bool: 代理是否可用
        """
        timeout = self.config.get("timeout", 15)
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url,
        })
        opener = urllib.request.build_opener(proxy_handler)

        # 创建一个忽略 SSL 证书错误的上下文（某些代理会篡改证书）
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        for test_url in self.TEST_URLS:
            try:
                req = urllib.request.Request(
                    test_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                context = ssl_ctx if test_url.startswith("https") else None
                response = opener.open(req, timeout=timeout, context=context) if context else opener.open(req, timeout=timeout)
                if response.status in (200, 301, 302):
                    return True
            except Exception:
                continue
        return False

    # ─── 安装代理 ────────────────────────────────────────────

    def install(self):
        """安装全局代理 opener

        遍历可用代理，安装第一个可用的。
        仅在脚本进程内生效，退出后自动恢复。
        """
        if not self.config.get("enabled", False):
            print("ℹ️  代理未启用（proxy_config.json 中 enabled=false）", file=sys.stderr)
            return False

        proxies = self.discover_proxies()

        if not proxies:
            print("⚠️  未找到任何代理配置，将使用直连", file=sys.stderr)
            return False

        print(f"🔍 发现 {len(proxies)} 个代理，开始逐个测试...", file=sys.stderr)

        # 保存原始 opener（用于恢复）
        self._original_opener = urllib.request._opener

        for i, proxy_url in enumerate(proxies):
            # 隐藏代理密码部分用于显示
            display = proxy_url
            if "@" in proxy_url:
                parts = proxy_url.split("@")
                display = f"...@{parts[-1]}"

            print(f"  [{i+1}/{len(proxies)}] 测试: {display}", file=sys.stderr)
            if self.test_proxy(proxy_url):
                self.current_proxy = proxy_url
                proxy_handler = urllib.request.ProxyHandler({
                    "http": proxy_url,
                    "https": proxy_url,
                })
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
                print(f"✅ 代理已启用: {display}", file=sys.stderr)
                return True
            else:
                print(f"  ❌ 不可用", file=sys.stderr)

        print("⚠️  所有代理均不可用，回退到直连", file=sys.stderr)
        return False

    def restore(self):
        """恢复原始网络设置（一般不需要手动调用，脚本退出即恢复）"""
        if self._original_opener:
            urllib.request.install_opener(self._original_opener)
            self._original_opener = None
            print("🔄 已恢复直连", file=sys.stderr)

    # ─── 便捷方法 ────────────────────────────────────────────

    def __repr__(self):
        status = f"当前代理: {self.current_proxy}" if self.current_proxy else "直连"
        return f"<ProxyManager {status}>"


# ─── 自测入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    """直接运行以测试代理功能"""
    print("=" * 50)
    print("代理管理器自测")
    print("=" * 50)

    pm = ProxyManager()

    print(f"\n配置状态: enabled={pm.config['enabled']}")
    print(f"手动代理数: {len(pm.config.get('manual_proxies', []))}")
    print(f"超时时间: {pm.config['timeout']}秒")

    proxies = pm.discover_proxies()
    print(f"\n发现代理总数: {len(proxies)}")
    for p in proxies:
        # 隐藏密码部分
        display = p
        if "@" in p:
            parts = p.split("@")
            display = f"...@{parts[-1]}"
        print(f"  • {display}")

    if pm.config["enabled"]:
        print("\n正在测试代理连通性...")
        installed = pm.install()
        if installed:
            print(f"\n✅ 成功启用代理: {pm.current_proxy}")
            # 再做一个实际的 HTTP 请求验证
            try:
                response = urllib.request.urlopen("http://httpbin.org/ip", timeout=10)
                print(f"外网 IP: {response.read().decode('utf-8')}")
            except Exception as e:
                print(f"验证请求失败: {e}")
        else:
            print("\n❌ 未能启用任何代理")
    else:
        print("\n⚠️  代理未启用，请在 proxy_config.json 中设置 enabled=true 并配置代理地址")
