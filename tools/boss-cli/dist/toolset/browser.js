import { getBrowserStatus, restartBrowser, startBrowser, stopBrowser, } from '../browser/index.js';

function envHeadless(env = process.env) {
    const value = String(env.BOSS_BROWSER_HEADLESS ?? '').trim().toLowerCase();
    return value === '1' || value === 'true' || value === 'yes' || value === 'y';
}

function selectedMode(mode) {
    return mode ?? (envHeadless() ? 'headless' : 'headful');
}

function formatRuntime(runtime) {
    return [
        `模式: ${runtime.mode}`,
        `PID: ${runtime.pid}`,
        `端口: ${runtime.port}`,
        `用户数据目录: ${runtime.userDataDir}`,
        `启动时间: ${runtime.startedAt}`,
    ];
}

export function formatBrowserStatus(status) {
    if (status.state === 'running') {
        return ['Boss 浏览器: running', ...formatRuntime(status.runtime)].join('\n');
    }
    if (status.state === 'unmanaged') {
        return [
            'Boss 浏览器: unmanaged',
            '检测到旧版或未受管的 Chrome 端点。生命周期命令不会关闭它；请先手动关闭一次。',
        ].join('\n');
    }
    if (status.state === 'stale') {
        return [
            'Boss 浏览器: stale',
            `清理后状态: ${status.effectiveState}`,
            `原因: ${status.reason}`,
            ...(status.cleanupError ? [`元数据清理失败: ${status.cleanupError}`] : []),
        ].join('\n');
    }
    return 'Boss 浏览器: stopped';
}

export async function runBrowserCommand(command) {
    if (command.action === 'status') {
        return formatBrowserStatus(await getBrowserStatus());
    }
    if (command.action === 'stop') {
        const result = await stopBrowser();
        return result.action === 'already-stopped'
            ? 'Boss 浏览器已经停止。'
            : 'Boss 浏览器已停止。';
    }
    const mode = selectedMode(command.mode);
    if (command.action === 'start') {
        const result = await startBrowser(mode);
        return [
            result.action === 'already-running' ? 'Boss 浏览器已在运行。' : 'Boss 浏览器已启动。',
            ...formatRuntime(result.runtime),
        ].join('\n');
    }
    if (command.action === 'restart') {
        const result = await restartBrowser(mode);
        return ['Boss 浏览器已重启。', ...formatRuntime(result.runtime)].join('\n');
    }
    throw new Error(`Unsupported browser action: ${String(command.action)}`);
}
