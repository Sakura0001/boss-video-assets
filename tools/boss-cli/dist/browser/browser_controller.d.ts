import { type BrowserMode, type BrowserRuntime, type BrowserRuntimeConfig, type BrowserRuntimeInspection, } from './browser_runtime.js';
type BrowserControllerOptions = {
    config?: BrowserRuntimeConfig;
    runtimeFile?: string;
    port?: number;
    userDataDir?: string;
    deps?: Record<string, unknown>;
};
export declare function resolveBrowserRuntimeConfig(options?: BrowserControllerOptions): BrowserRuntimeConfig;
export declare function getBrowserStatusUnlocked(options?: BrowserControllerOptions): Promise<BrowserRuntimeInspection>;
export declare function startBrowserUnlocked(mode: BrowserMode, options?: BrowserControllerOptions): Promise<{
    action: 'started' | 'already-running';
    runtime: BrowserRuntime;
}>;
export declare function stopBrowserUnlocked(options?: BrowserControllerOptions): Promise<{
    action: 'stopped';
    runtime: BrowserRuntime;
} | {
    action: 'already-stopped';
}>;
export declare function restartBrowserUnlocked(mode: BrowserMode, options?: BrowserControllerOptions): ReturnType<typeof startBrowserUnlocked>;
export declare function getBrowserStatus(options?: BrowserControllerOptions): Promise<BrowserRuntimeInspection>;
export declare function startBrowser(mode: BrowserMode, options?: BrowserControllerOptions): ReturnType<typeof startBrowserUnlocked>;
export declare function stopBrowser(options?: BrowserControllerOptions): ReturnType<typeof stopBrowserUnlocked>;
export declare function restartBrowser(mode: BrowserMode, options?: BrowserControllerOptions): ReturnType<typeof startBrowserUnlocked>;
