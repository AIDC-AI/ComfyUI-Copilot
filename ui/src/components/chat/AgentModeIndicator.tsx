/**
 * AgentModeIndicator — visual progress indicator for Agent Mode.
 * Shows the step-by-step plan with status icons and expand/collapse.
 * 
 * Enhanced by Claude Opus 4.6
 */

import React, { useState, useEffect, useMemo } from 'react';

// ----- types -----
export interface AgentStep {
    id: number;
    title: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
    result?: string;
}

export interface AgentPlan {
    total: number;
    pending: number;
    in_progress: number;
    completed: number;
    failed: number;
    tasks: AgentStep[];
}

interface AgentModeIndicatorProps {
    /** Raw text from agent — we try to extract plan JSON blocks */
    agentText?: string;
    /** Or pass the plan directly if already parsed */
    plan?: AgentPlan | null;
    /** Is the agent still running? */
    isRunning: boolean;
}

// Regex to find JSON blocks that look like plan_tasks output
const PLAN_REGEX = /\{"plan":\s*\[.*?\].*?"total_steps":\s*\d+\}/gs;
const STATUS_REGEX = /\{"total":\s*\d+.*?"tasks":\s*\[.*?\]\}/gs;

function tryExtractPlan(text: string): AgentPlan | null {
    if (!text) return null;
    try {
        // Try to find the latest status update
        const statusMatches = [...text.matchAll(STATUS_REGEX)];
        if (statusMatches.length > 0) {
            const latest = statusMatches[statusMatches.length - 1][0];
            const parsed = JSON.parse(latest);
            if (parsed.tasks && Array.isArray(parsed.tasks)) {
                return parsed as AgentPlan;
            }
        }
        // Fallback: try to find plan creation
        const planMatches = [...text.matchAll(PLAN_REGEX)];
        if (planMatches.length > 0) {
            const latest = planMatches[planMatches.length - 1][0];
            const parsed = JSON.parse(latest);
            if (parsed.plan && Array.isArray(parsed.plan)) {
                return {
                    total: parsed.total_steps,
                    pending: parsed.plan.filter((t: any) => t.status === 'pending').length,
                    in_progress: 0,
                    completed: 0,
                    failed: 0,
                    tasks: parsed.plan.map((t: any) => ({
                        id: t.id,
                        title: t.title,
                        status: t.status || 'pending',
                        result: t.result,
                    })),
                };
            }
        }
    } catch {
        // Ignore parse errors
    }
    return null;
}

const statusIcon = (status: string) => {
    switch (status) {
        case 'completed': return '✅';
        case 'in_progress': return '⏳';
        case 'failed': return '❌';
        case 'skipped': return '⏭️';
        default: return '○';
    }
};

const statusColor = (status: string) => {
    switch (status) {
        case 'completed': return 'text-green-600';
        case 'in_progress': return 'text-blue-600 font-semibold';
        case 'failed': return 'text-red-500';
        case 'skipped': return 'text-gray-400 line-through';
        default: return 'text-gray-500';
    }
};

export const AgentModeIndicator: React.FC<AgentModeIndicatorProps> = ({
    agentText,
    plan: externalPlan,
    isRunning,
}) => {
    const [expanded, setExpanded] = useState(true);

    const plan = useMemo(() => {
        if (externalPlan) return externalPlan;
        return tryExtractPlan(agentText || '');
    }, [externalPlan, agentText]);

    // Auto-collapse when done
    useEffect(() => {
        if (!isRunning && plan && plan.completed === plan.total) {
            // Keep expanded briefly so user sees the final state
            const t = setTimeout(() => setExpanded(false), 3000);
            return () => clearTimeout(t);
        }
    }, [isRunning, plan]);

    if (!plan || plan.tasks.length === 0) {
        if (isRunning) {
            return (
                <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700 mb-2">
                    <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>🤖 Agent Mode — Planning...</span>
                </div>
            );
        }
        return null;
    }

    const completedCount = plan.completed;
    const totalCount = plan.total;
    const progressPct = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

    return (
        <div className="mb-2 border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
            {/* Header bar */}
            <button
                className="w-full flex items-center justify-between px-3 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors text-xs"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2">
                    <span className="text-base">🤖</span>
                    <span className="font-semibold text-gray-700">
                        Agent Mode
                    </span>
                    <span className="text-gray-500">
                        {completedCount}/{totalCount} steps
                    </span>
                    {isRunning && (
                        <svg className="animate-spin h-3 w-3 text-blue-500" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                    )}
                </div>
                <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Progress bar */}
            <div className="h-1 bg-gray-100">
                <div
                    className="h-full bg-gradient-to-r from-blue-400 to-indigo-500 transition-all duration-500 ease-out"
                    style={{ width: `${progressPct}%` }}
                />
            </div>

            {/* Step list */}
            {expanded && (
                <div className="px-3 py-2 space-y-1">
                    {plan.tasks.map((step) => (
                        <div key={step.id} className={`flex items-start gap-2 text-xs ${statusColor(step.status)}`}>
                            <span className="flex-shrink-0 mt-0.5">{statusIcon(step.status)}</span>
                            <div className="flex-1 min-w-0">
                                <span>{step.title}</span>
                                {step.result && step.status !== 'pending' && (
                                    <p className="text-[10px] text-gray-400 mt-0.5 truncate" title={step.result}>
                                        {step.result}
                                    </p>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default AgentModeIndicator;
