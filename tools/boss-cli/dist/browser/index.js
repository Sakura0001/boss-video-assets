/**
 * 浏览器：CDP 连接与会话（统一出口）。
 */
export * from './timing.js';
export * from './human_delay.js';
export { hideAgentOperatingIndicator, showAgentOperatingIndicator, } from './agent_operating_indicator.js';
export { resumeHeight, setTempHeight, snapshotBossPageViewport, } from './viewport_temp.js';
export { connectBrowser, createPageCDPSession, defaultViewportFromEnv, launchManagedBrowser, LAUNCH_ARGS_ALLOW_ALL_CORS, LAUNCH_ARGS_LESS_AUTOMATION, wasLastChromeLaunchHeadless, } from './cdp_browser.js';
export { getBrowserStatus, getBrowserStatusUnlocked, resolveBrowserRuntimeConfig, restartBrowser, restartBrowserUnlocked, startBrowser, startBrowserUnlocked, stopBrowser, stopBrowserUnlocked, } from './browser_controller.js';
export { inspectBrowserRuntime, probeBrowserEndpoint, readBrowserRuntime, removeBrowserRuntime, writeBrowserRuntime, } from './browser_runtime.js';
export { detachBrowserSession, disconnectBrowserSession, ensureAndGetBrowser, ensureBrowserSession, getBrowserRef, getPageRef, setSessionPage, } from './browser_session.js';
//# sourceMappingURL=index.js.map
