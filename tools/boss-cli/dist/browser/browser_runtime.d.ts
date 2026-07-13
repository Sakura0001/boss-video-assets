export type BrowserMode = 'headless' | 'headful';
export type BrowserRuntime = {
    schemaVersion: 1;
    pid: number;
    port: number;
    mode: BrowserMode;
    userDataDir: string;
    startedAt: string;
};
export type BrowserRuntimeConfig = {
    filePath: string;
    port: number;
    userDataDir: string;
};
export type BrowserRuntimeInspection =
    | { state: 'stopped' }
    | { state: 'unmanaged'; webSocketDebuggerUrl: string }
    | { state: 'running'; runtime: BrowserRuntime; webSocketDebuggerUrl: string }
    | {
        state: 'stale';
        effectiveState: 'stopped' | 'unmanaged';
        reason: string;
        webSocketDebuggerUrl?: string;
        cleanupError?: string;
    };
export declare const BROWSER_RUNTIME_SCHEMA_VERSION: 1;
export declare function parseBrowserRuntime(value: unknown): BrowserRuntime;
export declare function readBrowserRuntime(filePath?: string): Promise<BrowserRuntime | null>;
export declare function writeBrowserRuntime(runtime: BrowserRuntime, filePath?: string): Promise<BrowserRuntime>;
export declare function removeBrowserRuntime(filePath?: string): Promise<void>;
export declare function processExists(pid: number): Promise<boolean>;
export declare function probeBrowserEndpoint(port: number, timeoutMs?: number): Promise<string | undefined>;
export declare function inspectBrowserRuntime(config: BrowserRuntimeConfig, deps?: {
    readRuntime?: (filePath: string) => Promise<BrowserRuntime | null>;
    removeRuntime?: (filePath: string) => Promise<void>;
    processExists?: (pid: number) => Promise<boolean>;
    probeEndpoint?: (port: number) => Promise<string | undefined>;
}): Promise<BrowserRuntimeInspection>;
