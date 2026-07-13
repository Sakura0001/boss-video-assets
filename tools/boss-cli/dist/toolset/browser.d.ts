import { type BrowserRuntimeInspection } from '../browser/browser_runtime.js';
export type BrowserCommand = {
    action: 'status' | 'stop';
} | {
    action: 'start' | 'restart';
    mode?: 'headless' | 'headful';
};
export declare function formatBrowserStatus(status: BrowserRuntimeInspection): string;
export declare function runBrowserCommand(command: BrowserCommand): Promise<string>;
