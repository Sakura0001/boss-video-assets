export type BossCommandPacingProfile = 'initial_outreach' | 'normal' | 'idle_unread_check';
export declare const BOSS_COMMAND_PACING_PROFILES: {
    readonly initial_outreach: {
        readonly minMs: 4000;
        readonly maxMs: 6000;
    };
    readonly normal: {
        readonly minMs: 6000;
        readonly maxMs: 10000;
    };
    readonly idle_unread_check: {
        readonly minMs: 30000;
        readonly maxMs: 60000;
    };
};
export type CommandPacingDependencies = {
    stateFile?: string;
    lockFile?: string;
    now?: () => number;
    sleep?: (ms: number) => Promise<void>;
    sampleDelay?: (profile: BossCommandPacingProfile) => number;
};
export declare function getBossCommandPacingProfile(command: string): BossCommandPacingProfile | undefined;
/**
 * Serialize public Boss commands and enforce a randomized wait persisted across CLI processes.
 * The state intentionally stores no candidate, message, resume, cookie, or recruiting data.
 */
export declare function runPacedBossCommand<T>(command: string, callback: () => Promise<T>, dependencies?: CommandPacingDependencies): Promise<T>;
//# sourceMappingURL=command_pacing.d.ts.map