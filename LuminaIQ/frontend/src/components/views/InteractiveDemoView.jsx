import { useState, useEffect, useRef, useCallback } from 'react';
import {
    Cpu,
    Play,
    RotateCcw,
    Code2,
    X,
    Loader2,
    Sparkles,
    ChevronDown,
    Clock,
    Trash2,
    Copy,
    Check,
    Maximize2,
    Minimize2,
    Info,
    Wand2,
} from 'lucide-react';
import { generateInteractiveDemo } from '../../api';
import { recordActivity } from '../../utils/studyActivity';

// ═══════════════════════════════════════════════════════════════════════════
//  INTERACTIVE LIVE DEMO VIEW
//  AI-generated HTML/CSS/JS visualizations rendered in sandboxed iframes
// ═══════════════════════════════════════════════════════════════════════════

const InteractiveDemoView = ({ projectId, availableTopics = [], selectedDocuments = [] }) => {
    // Generation state
    const [topic, setTopic] = useState('');
    const [additionalInfo, setAdditionalInfo] = useState('');
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);

    // Current demo
    const [currentDemo, setCurrentDemo] = useState(null);

    // UI state
    const [showCode, setShowCode] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [copied, setCopied] = useState(false);
    const [showTopicDropdown, setShowTopicDropdown] = useState(false);
    const [topicFilter, setTopicFilter] = useState('');
    const [showHistory, setShowHistory] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);

    // History (session storage)
    const [history, setHistory] = useState(() => {
        try {
            const saved = sessionStorage.getItem(`lumina_demos_${projectId}`);
            return saved ? JSON.parse(saved) : [];
        } catch { return []; }
    });

    // Refs
    const iframeRef = useRef(null);
    const dropdownRef = useRef(null);
    const inputRef = useRef(null);

    // Persist history
    useEffect(() => {
        sessionStorage.setItem(`lumina_demos_${projectId}`, JSON.stringify(history.slice(0, 20)));
    }, [history, projectId]);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setShowTopicDropdown(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Filter topics
    const filteredTopics = availableTopics.filter(t =>
        t.toLowerCase().includes(topicFilter.toLowerCase())
    );

    // ── Generate demo ──────────────────────────────────────────────────────
    const handleGenerate = useCallback(async () => {
        if (!topic.trim()) return;

        setGenerating(true);
        setError(null);
        setShowCode(false);

        try {
            const result = await generateInteractiveDemo(
                projectId,
                topic.trim(),
                additionalInfo.trim(),
                availableTopics.slice(0, 10)
            );

            const demo = {
                ...result,
                topic: topic.trim(),
                additionalInfo: additionalInfo.trim(),
                timestamp: Date.now(),
                id: `demo_${Date.now()}`,
            };

            setCurrentDemo(demo);
            setHistory(prev => [demo, ...prev.filter(d => d.id !== demo.id)]);
            recordActivity(projectId, 'interactive_demo', { action: 'generate', topic: topic.trim() });
        } catch (err) {
            console.error('Demo generation failed:', err);
            setError(err?.response?.data?.detail || err.message || 'Failed to generate demo');
        } finally {
            setGenerating(false);
        }
    }, [topic, additionalInfo, projectId, availableTopics]);

    // ── Copy HTML ──────────────────────────────────────────────────────────
    const handleCopy = async () => {
        if (!currentDemo?.html_code) return;
        try {
            await navigator.clipboard.writeText(currentDemo.html_code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback
            const ta = document.createElement('textarea');
            ta.value = currentDemo.html_code;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // ── Load from history ──────────────────────────────────────────────────
    const loadFromHistory = (demo) => {
        setCurrentDemo(demo);
        setTopic(demo.topic);
        setAdditionalInfo(demo.additionalInfo || '');
        setShowHistory(false);
        setShowCode(false);
    };

    // ── Delete from history ────────────────────────────────────────────────
    const deleteFromHistory = (id, e) => {
        e.stopPropagation();
        setHistory(prev => prev.filter(d => d.id !== id));
        if (currentDemo?.id === id) {
            setCurrentDemo(null);
        }
    };

    // ── Suggestion chips ───────────────────────────────────────────────────
    const suggestions = [
        { label: "Newton's 3rd Law (3D)", prompt: "A 3D simulation of Newton's 3rd Law using Three.js, showing a rocket firing engines (action) and flying in outer space (reaction) with interactive fly/launch buttons." },
        { label: '3D Planet Generator', prompt: 'A procedurally generated 3D planet with terrain, atmosphere, and rotation controls using Three.js' },
        { label: 'Sorting Visualizer', prompt: 'An animated sorting algorithm visualizer comparing bubble sort, merge sort, and quicksort' },
        { label: 'Physics Sandbox', prompt: 'A 2D physics simulation with bouncing balls, gravity slider, and friction controls using Matter.js' },
        { label: 'Neural Network', prompt: 'An interactive neural network diagram showing forward propagation with adjustable weights' },
        { label: 'Binary Tree', prompt: 'An interactive binary search tree with insert, delete, and balance operations' },
    ];

    // ── Fullscreen toggle ──────────────────────────────────────────────────
    const toggleFullscreen = () => {
        setIsFullscreen(!isFullscreen);
    };

    // ── Time formatting ────────────────────────────────────────────────────
    const formatTime = (ts) => {
        const d = new Date(ts);
        const now = new Date();
        const diff = now - d;
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return d.toLocaleDateString();
    };

    // ═══ FULLSCREEN OVERLAY ════════════════════════════════════════════════
    if (isFullscreen && currentDemo) {
        return (
            <div className="fixed inset-0 z-[100] bg-black">
                <button
                    onClick={toggleFullscreen}
                    className="absolute top-4 right-4 z-10 p-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors backdrop-blur-sm"
                >
                    <Minimize2 className="h-5 w-5 text-white" />
                </button>
                <iframe
                    ref={iframeRef}
                    srcDoc={currentDemo.html_code}
                    sandbox="allow-scripts allow-same-origin"
                    className="w-full h-full border-0"
                    title="Interactive Demo Fullscreen"
                />
            </div>
        );
    }

    // ═══ MAIN LAYOUT ═══════════════════════════════════════════════════════
    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* ── Header ──────────────────────────────────────────────── */}
            <div className="shrink-0 border-b border-[#E6D5CC]/50 bg-white/80 backdrop-blur-sm">
                <div className="px-4 md:px-6 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="h-10 w-10 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/20">
                                <Cpu className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <h2 className="text-lg font-bold text-[#4A3B32]">Interactive Live Demo</h2>
                                    <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-violet-100 text-violet-700 border border-violet-200 rounded">
                                        Preview Beta
                                    </span>
                                </div>
                                <p className="text-xs text-[#8a6a5c]">AI-generated interactive visualizations</p>
                            </div>
                        </div>

                        {/* History toggle */}
                        {history.length > 0 && (
                            <button
                                onClick={() => setShowHistory(!showHistory)}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                                    showHistory
                                        ? 'bg-[#C8A288] text-white'
                                        : 'bg-[#FDF6F0] text-[#8a6a5c] hover:bg-[#E6D5CC]'
                                }`}
                            >
                                <Clock className="h-4 w-4" />
                                <span className="hidden sm:inline">History</span>
                                <span className="bg-white/20 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                                    {history.length}
                                </span>
                            </button>
                        )}
                    </div>

                    {/* ── Topic Input Row ──────────────────────────────── */}
                    <div className="flex flex-col sm:flex-row gap-3">
                        <div className="flex-1 relative" ref={dropdownRef}>
                            <div className="flex items-center bg-[#FDF6F0] border border-[#E6D5CC] rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-violet-400 focus-within:border-transparent transition-all">
                                <Sparkles className="h-4 w-4 text-violet-400 ml-3 shrink-0" />
                                <input
                                    ref={inputRef}
                                    type="text"
                                    value={topic}
                                    onChange={(e) => {
                                        setTopic(e.target.value);
                                        setTopicFilter(e.target.value);
                                        if (e.target.value.length > 0 && availableTopics.length > 0) {
                                            setShowTopicDropdown(true);
                                        }
                                    }}
                                    onFocus={() => {
                                        if (availableTopics.length > 0) setShowTopicDropdown(true);
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && topic.trim()) {
                                            e.preventDefault();
                                            setShowTopicDropdown(false);
                                            handleGenerate();
                                        }
                                    }}
                                    placeholder="Enter a topic to visualize..."
                                    className="flex-1 px-3 py-3 bg-transparent outline-none text-[#4A3B32] text-sm placeholder-[#8a6a5c]/50"
                                />
                                {availableTopics.length > 0 && (
                                    <button
                                        onClick={() => setShowTopicDropdown(!showTopicDropdown)}
                                        className="p-2 text-[#8a6a5c] hover:text-[#4A3B32] transition-colors"
                                    >
                                        <ChevronDown className={`h-4 w-4 transition-transform ${showTopicDropdown ? 'rotate-180' : ''}`} />
                                    </button>
                                )}
                            </div>

                            {/* Topic Dropdown */}
                            {showTopicDropdown && filteredTopics.length > 0 && (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#E6D5CC] rounded-xl shadow-xl max-h-48 overflow-y-auto z-30 custom-scrollbar">
                                    {filteredTopics.map((t, i) => (
                                        <button
                                            key={i}
                                            onClick={() => {
                                                setTopic(t);
                                                setShowTopicDropdown(false);
                                            }}
                                            className="w-full text-left px-4 py-2.5 text-sm text-[#4A3B32] hover:bg-[#FDF6F0] transition-colors first:rounded-t-xl last:rounded-b-xl"
                                        >
                                            {t}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="flex gap-2 shrink-0">
                            {/* Advanced toggle */}
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className={`p-3 rounded-xl border transition-colors ${
                                    showAdvanced
                                        ? 'bg-violet-50 border-violet-300 text-violet-600'
                                        : 'bg-[#FDF6F0] border-[#E6D5CC] text-[#8a6a5c] hover:border-violet-300'
                                }`}
                                title="Additional instructions"
                            >
                                <Wand2 className="h-4 w-4" />
                            </button>

                            {/* Generate button */}
                            <button
                                onClick={handleGenerate}
                                disabled={generating || !topic.trim()}
                                className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-violet-500 to-indigo-600 text-white rounded-xl font-semibold text-sm hover:from-violet-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30"
                            >
                                {generating ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        <span className="hidden sm:inline">Generating...</span>
                                    </>
                                ) : (
                                    <>
                                        <Play className="h-4 w-4" />
                                        <span className="hidden sm:inline">Generate</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Advanced textarea */}
                    {showAdvanced && (
                        <div className="mt-3 animate-in slide-in-from-top-2">
                            <textarea
                                value={additionalInfo}
                                onChange={(e) => setAdditionalInfo(e.target.value)}
                                placeholder="Add extra instructions... e.g., 'Use 3D canvas', 'Focus on memory layout', 'Include step-by-step animation', 'Add a quiz at the end'"
                                rows={2}
                                className="w-full px-4 py-2.5 bg-[#FDF6F0] border border-[#E6D5CC] rounded-xl text-sm text-[#4A3B32] placeholder-[#8a6a5c]/40 outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent resize-none"
                            />
                        </div>
                    )}

                    {/* Suggestion chips (shown only when no topic is entered) */}
                    {!topic && !currentDemo && (
                        <div className="mt-3 flex flex-wrap gap-2">
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    onClick={() => {
                                        setTopic(s.prompt);
                                        setShowTopicDropdown(false);
                                    }}
                                    className="px-3 py-1.5 bg-white border border-[#E6D5CC] rounded-full text-xs text-[#8a6a5c] hover:border-violet-300 hover:text-violet-600 hover:bg-violet-50 transition-all"
                                >
                                    {s.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Content Area ─────────────────────────────────────────── */}
            <div className="flex-1 flex min-h-0 overflow-hidden">
                {/* History panel (slide in) */}
                {showHistory && (
                    <div className="w-64 shrink-0 border-r border-[#E6D5CC]/50 bg-white overflow-y-auto custom-scrollbar">
                        <div className="p-3 border-b border-[#E6D5CC]/50">
                            <p className="text-xs font-semibold text-[#4A3B32] uppercase tracking-wider">Recent Demos</p>
                        </div>
                        <div className="p-2 space-y-1">
                            {history.map((demo) => (
                                <button
                                    key={demo.id}
                                    onClick={() => loadFromHistory(demo)}
                                    className={`w-full text-left p-3 rounded-xl transition-colors group ${
                                        currentDemo?.id === demo.id
                                            ? 'bg-violet-50 border border-violet-200'
                                            : 'hover:bg-[#FDF6F0]'
                                    }`}
                                >
                                    <p className="text-sm font-medium text-[#4A3B32] truncate">{demo.topic}</p>
                                    <p className="text-[10px] text-[#8a6a5c] mt-1">{formatTime(demo.timestamp)}</p>
                                    <button
                                        onClick={(e) => deleteFromHistory(demo.id, e)}
                                        className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-red-50 rounded transition-all"
                                    >
                                        <Trash2 className="h-3 w-3 text-red-400" />
                                    </button>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Main content */}
                <div className="flex-1 flex flex-col min-h-0">
                    {/* ── Error ────────────────────────────────────────── */}
                    {error && (
                        <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
                            <Info className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-red-700">Generation Failed</p>
                                <p className="text-xs text-red-500 mt-1">{error}</p>
                            </div>
                            <button onClick={() => setError(null)} className="ml-auto p-1 hover:bg-red-100 rounded">
                                <X className="h-4 w-4 text-red-400" />
                            </button>
                        </div>
                    )}

                    {/* ── Generating state ─────────────────────────────── */}
                    {generating && (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center">
                                <div className="relative mb-6">
                                    <div className="h-20 w-20 mx-auto rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/30">
                                        <Cpu className="h-10 w-10 text-white animate-pulse" />
                                    </div>
                                    <div className="absolute -inset-3 rounded-3xl border-2 border-violet-300/30 animate-ping" style={{ animationDuration: '2s' }} />
                                </div>
                                <h3 className="text-lg font-bold text-[#4A3B32] mb-2">Crafting your experience...</h3>
                                <p className="text-sm text-[#8a6a5c] max-w-xs mx-auto">
                                    The AI is generating an interactive visualization for <span className="font-semibold text-violet-600">"{topic}"</span>
                                </p>
                                <p className="text-xs text-[#8a6a5c]/50 mt-3">This may take 15-30 seconds</p>
                            </div>
                        </div>
                    )}

                    {/* ── Rendered demo ────────────────────────────────── */}
                    {!generating && currentDemo && (
                        <div className="flex-1 flex flex-col min-h-0">
                            {/* Toolbar */}
                            <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-[#FDF6F0]/80 border-b border-[#E6D5CC]/30">
                                <div className="flex items-center gap-2 min-w-0">
                                    <div className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
                                    <span className="text-xs font-medium text-[#4A3B32] truncate">{currentDemo.topic}</span>
                                </div>
                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => setShowCode(!showCode)}
                                        className={`p-1.5 rounded-lg text-xs transition-colors flex items-center gap-1.5 ${
                                            showCode
                                                ? 'bg-violet-100 text-violet-600'
                                                : 'hover:bg-[#E6D5CC] text-[#8a6a5c]'
                                        }`}
                                        title="View source code"
                                    >
                                        <Code2 className="h-3.5 w-3.5" />
                                        <span className="hidden sm:inline">Code</span>
                                    </button>
                                    <button
                                        onClick={handleCopy}
                                        className="p-1.5 rounded-lg hover:bg-[#E6D5CC] text-[#8a6a5c] transition-colors flex items-center gap-1.5"
                                        title="Copy HTML"
                                    >
                                        {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setTopic(currentDemo.topic);
                                            setAdditionalInfo(currentDemo.additionalInfo || '');
                                            handleGenerate();
                                        }}
                                        className="p-1.5 rounded-lg hover:bg-[#E6D5CC] text-[#8a6a5c] transition-colors"
                                        title="Regenerate"
                                    >
                                        <RotateCcw className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                        onClick={toggleFullscreen}
                                        className="p-1.5 rounded-lg hover:bg-[#E6D5CC] text-[#8a6a5c] transition-colors"
                                        title="Fullscreen"
                                    >
                                        <Maximize2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            </div>

                            {/* Content: iframe or code */}
                            <div className="flex-1 min-h-0 relative">
                                {showCode ? (
                                    <div className="absolute inset-0 overflow-auto bg-[#1e1e2e] custom-scrollbar">
                                        <pre className="p-4 text-xs font-mono text-[#cdd6f4] whitespace-pre-wrap break-words leading-relaxed">
                                            {currentDemo.html_code}
                                        </pre>
                                    </div>
                                ) : (
                                    <iframe
                                        ref={iframeRef}
                                        srcDoc={currentDemo.html_code}
                                        sandbox="allow-scripts allow-same-origin"
                                        className="absolute inset-0 w-full h-full border-0 bg-white"
                                        title="Interactive Demo"
                                    />
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── Empty state ──────────────────────────────────── */}
                    {!generating && !currentDemo && (
                        <div className="flex-1 flex items-center justify-center p-8">
                            <div className="text-center max-w-md">
                                <div className="h-20 w-20 mx-auto mb-6 bg-gradient-to-br from-violet-100 to-indigo-100 rounded-2xl flex items-center justify-center">
                                    <Cpu className="h-10 w-10 text-violet-400" />
                                </div>
                                <h3 className="text-xl font-bold text-[#4A3B32] mb-3">
                                    Bring concepts to life
                                </h3>
                                <p className="text-sm text-[#8a6a5c] mb-6 leading-relaxed">
                                    Type any topic above and the AI will generate a fully interactive
                                    HTML visualization with animations, controls, and educational content.
                                </p>
                                <div className="grid grid-cols-2 gap-3 text-left">
                                    {[
                                        { icon: '🎯', text: 'Interactive controls & animations' },
                                        { icon: '🧠', text: 'Teaches concepts visually' },
                                        { icon: '⚡', text: 'Runs entirely in browser' },
                                        { icon: '📋', text: 'Copy & share the HTML code' },
                                    ].map((item, i) => (
                                        <div key={i} className="flex items-center gap-2 p-3 bg-[#FDF6F0] rounded-xl">
                                            <span className="text-base">{item.icon}</span>
                                            <span className="text-xs text-[#4A3B32]">{item.text}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default InteractiveDemoView;
