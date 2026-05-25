/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, FormEvent } from 'react';
import { 
  Send, 
  RefreshCw, 
  Settings, 
  Bot, 
  User, 
  Plus, 
  Check, 
  CheckCircle2, 
  AlertTriangle, 
  Clipboard, 
  Bell, 
  FileText, 
  CheckSquare, 
  Sparkles, 
  Eye, 
  ExternalLink, 
  ShieldAlert, 
  Trash2, 
  HelpCircle,
  MessageSquare,
  Clock,
  Briefcase,
  Lightbulb,
  AlertCircle
} from 'lucide-react';

// Definitions for local structures
interface TaskHistory {
  id: string;
  command: string;
  draftMessage: string;
  persona: string;
  timestamp: string;
  automationType: string;
  targetAudience: string;
  dispatchedToLine: boolean;
}

interface SimulatedLineMessage {
  id: string;
  sender: 'ai_notify' | 'user';
  text: string;
  timestamp: string;
}

export default function App() {
  // --- States ---
  const [lineToken, setLineToken] = useState<string>(() => {
    return localStorage.getItem('line_agent_token') || '';
  });
  const [sendToRealLine, setSendToRealLine] = useState<boolean>(() => {
    return localStorage.getItem('line_agent_send_real') === 'true';
  });
  const [commandPrompt, setCommandPrompt] = useState<string>('');
  const [selectedPersona, setSelectedPersona] = useState<string>('secretary');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isSendingToLine, setIsSendingToLine] = useState<boolean>(false);
  
  // Terminal log simulation states
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [activeLogIndex, setActiveLogIndex] = useState<number>(-1);
  
  // Results
  const [agentResult, setAgentResult] = useState<any | null>(null);
  const [editableDraft, setEditableDraft] = useState<string>('');
  
  // Task Automations history
  const [historyList, setHistoryList] = useState<TaskHistory[]>(() => {
    const saved = localStorage.getItem('line_agent_history');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) { return []; }
    }
    return [
      {
        id: '1',
        command: "ตรวจหาฝุ่น PM2.5 และร่างสุนทรพจน์สั้นตักเตือนพนักงานให้ดูแลสุขภาพและสวมหน้ากากอนามัยกรณีออกนอกอาคาร",
        draftMessage: "📢 [ประกาศด่วน: ข้อห่วงใยด้านสุขภาพจากแอดมิน]\n\nเรียน เพื่อนพนักงานผู้รักสุขภาพทุกท่านค่ะ 😷\n\nสืบเนื่องจากวันนี้ค่าฝุ่นละอองขนาดเล็ก PM 2.5 ในพื้นที่ข้างนอกสำนักงานมีแนวโน้มพุ่งสูงเกินเกณฑ์มาตรฐานที่เป็นอันตรายต่อระบบทางเดินหายใจ\n\nทางฝ่ายแอดมินจึงใคร่ขอความร่วมมือและขอแสดงความเป็นห่วงแก่ทุกท่าน ดังนี้ค่ะ:\n\n🔹 หลีกเลี่ยงกิจกรรมกลางแจ้งเป็นเวลานาน\n🔹 สวมหน้ากากป้องกันฝุ่น (N95 หรือเทียบเท่า) ทุกครั้งก่อนก้าวพ้นอาคาร\n🔹 หากท่านใดเริ่มมีอาการเคืองตา แน่นหน้าอก หรือไอเรื้อรัง สามารถติดต่อขอรับยาสามัญเบื้องต้นได้ที่ห้องพยาบาลชั้น 2 ทันทีค่ะ\n\nด้วยรักและห่วงใย อยากเห็นทุกคนทำงานด้วยรอยยิ้มและสุขภาพที่แข็งแรงนะคะ 💖✨",
        persona: "secretary",
        timestamp: "2026-05-24 11:32:10",
        automationType: "announcement",
        targetAudience: "พนักงานในสำนักงาน",
        dispatchedToLine: true
      },
      {
        id: '2',
        command: "เตือนทีมไอทีว่าบ่ายสี่ครึ่งวันนี้จะมีอัปเดตเซิร์ฟเวอร์ฐานข้อมูลห้ามทำธุรกรรมการเงินช่วงนี้",
        draftMessage: "🚨 [NOTICE: DB Server Maintenance Notice]\n\nถึง ทีมวิศวกรไอทีและฝ่ายที่เกี่ยวข้องทุกคนครับ 🛠️\n\nตามตารางงานการบำรุงรักษาระบบหลัก ในวันนี้ช่วงเย็น เวลา 16:30 น. เป็นต้นไป\n\nทางเราจะเริ่มทำการอัปเดต Patch ฐานข้อมูลหลัก ซึ่งจะส่งผลให้ระบบงานบางส่วนใช้งานไม่ได้ชั่วคราว:\n\n⚠️ ของดเว้นการส่งข้อมูล หรือทำธุรกรรมการเงินทุกประเภทผ่านช่องทาง Database ในช่วงเวลา 16:30 - 17:30 น. โดยเด็ดขาด!\n\nรบกวนรับทราบและแจ้งทีมงานในสังกัดเพื่อเตรียมความพร้อมด้วยครับ หากหน้างานติดปัญหากรุณาแจ้งมาในช่องแชท Tech-Support ทันทีครับ\n\nขอบคุณมากครับ",
        persona: "admin",
        timestamp: "2026-05-24 10:15:22",
        automationType: "reminder",
        targetAudience: "ทีมงานระบบไอทีและบัญชี",
        dispatchedToLine: false
      }
    ];
  });

  // Simulated LINE Chat screen
  const [lineChatMessages, setLineChatMessages] = useState<SimulatedLineMessage[]>([
    {
      id: 'welcome1',
      sender: 'ai_notify',
      text: 'สวัสดีค่ะ! ดิฉันคือ "เลขา AI ประจำกลุ่ม LINE" ยินดีต้อนรับเข้าสู่อีมูเลเตอร์จำลองช่องทางแจ้งเตือนค่ะ 👩‍💼✨',
      timestamp: '12:00'
    },
    {
      id: 'welcome2',
      sender: 'ai_notify',
      text: 'คุณสามารถป้อนคำสั่งงานบนคอนโซลด้านซ้าย เช่นสั่งให้ดิฉันแต่งคำประกาศเตือนสติ, นัดประชุมบ่าย, หรือมอบหมายกิจกรรมต่างๆ แล้วสั่งแชร์ลงกลุ่มได้ทันทีค่ะ!',
      timestamp: '12:01'
    }
  ]);

  // Toast State
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' | null }>({
    message: '',
    type: null
  });

  // Help Modal Toggle
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);

  // --- Scroll Ref to make simulated LINE chat always stick to bottom ---
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lineChatMessages]);

  // Persists token
  useEffect(() => {
    localStorage.setItem('line_agent_token', lineToken);
  }, [lineToken]);

  // Persists dispatch preferences
  useEffect(() => {
    localStorage.setItem('line_agent_send_real', String(sendToRealLine));
  }, [sendToRealLine]);

  // Persists task history List
  useEffect(() => {
    localStorage.setItem('line_agent_history', JSON.stringify(historyList));
  }, [historyList]);

  // --- Show custom Toast utility ---
  const showToast = (message: string, type: 'success' | 'error' | 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast({ message: '', type: null });
    }, 4500);
  };

  // --- Presets click ---
  const handleApplyPreset = (text: string, persona: string) => {
    setCommandPrompt(text);
    setSelectedPersona(persona);
    showToast(`ใช้ตัวอย่างคำสั่งเป้าหมายแล้ว!`, 'info');
  };

  // --- Run AI Agent Parser (Calls Server Gemini API) ---
  const handleRunAgent = async (e: FormEvent) => {
    e.preventDefault();
    if (!commandPrompt.trim()) {
      showToast('กรุณากรอกคำสั่งหรือความต้องการของคุณก่อนสั่งงานแก่อันดับแรก', 'error');
      return;
    }

    setIsAnalyzing(true);
    setAgentResult(null);
    setEditableDraft('');
    
    // Simulate terminal logs on frontend to look like an expert agent in action
    const simulatedSteps = [
      "🔄 [AGENT]: ได้รับคำสั่งเป้าหมายใหม่ ค้นหาคำสำคัญและระบุเจตนาของผู้ใช้...",
      `📍 [AGENT-CLASSIFY]: กำลังประมวลผลการจัดบทบาทสมมติเป็น "${selectedPersona}" เพื่อเตรียมร่างถ้อยคำ...`,
      `🧠 [AI-THINKING]: เรียกประมวลผลผ่านโมเดล Gemini 3.5 Flash ในฝั่งเซิร์ฟเวอร์...`,
      "✍️ [COMPLEX-DRAFT]: สังเคราะห์เนื้อหาความละเอียดอ่อน ออกแบบและใส่ลูกเล่นจัดแต่งอิโมจิ...",
      "🔍 [SELF-REVIEW]: ทำการตรวจสอบความเหมาะสมของถ้อยคำ สุภาพ เรียบร้อย ตรวจหงิกคำผิด...",
      "🎉 [DRAFT-COMPLETE]: การสังเคราะห์โครงสร้างสำเร็จสมบูรณ์ เตรียมส่งหน้าต่างควบคุม!"
    ];

    setTerminalLogs([]);
    setActiveLogIndex(0);

    // Dynamic log generator during fetch wait
    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < simulatedSteps.length) {
        setTerminalLogs(prev => [...prev, simulatedSteps[currentStep]]);
        setActiveLogIndex(currentStep);
        currentStep++;
      } else {
        clearInterval(interval);
      }
    }, 700);

    try {
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: commandPrompt,
          agentPersona: selectedPersona,
          lineToken: lineToken
        })
      });

      const data = await response.json();
      clearInterval(interval); // finish simulation immediately when data arrives

      if (data.success && data.agentResult) {
        // Complete remaining logs instantly
        setTerminalLogs(simulatedSteps);
        setActiveLogIndex(simulatedSteps.length - 1);

        setAgentResult(data.agentResult);
        setEditableDraft(data.agentResult.draftMessage);
        showToast('เลขา AI ร่างโครงสร้างและกระบวนการทำงานเสร็จสมบูรณ์!', 'success');
      } else {
        showToast(data.error || 'เกิดข้อผิดพลาดในการวิเคราะห์จากระบบ AI', 'error');
        setTerminalLogs(prev => [...prev, `❌ [ERROR]: ไม่สามารถสังเคราะห์ข้อความได้สำเร็จ: ${data.error}`]);
      }
    } catch (err: any) {
      clearInterval(interval);
      console.error(err);
      showToast('เกิดข้อผิดพลาดในการเชื่อมต่อเครือข่ายไปยังเซิร์ฟเวอร์เบื้องหลัง', 'error');
      setTerminalLogs(prev => [...prev, `❌ [CATASTROPHIC ERROR]: การสื่อสารเครือข่ายล้มเหลว`]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // --- Dispatch Draft text directly to LINE Notify ---
  const handleDispatchToLine = async () => {
    const textToSend = editableDraft || (agentResult ? agentResult.draftMessage : '');
    
    if (!textToSend.trim()) {
      showToast('ไม่พบยอดโครงร่างข้อความสำหรับนำไปเผยแพร่ลงไลน์', 'error');
      return;
    }

    // Capture simulation or real destination
    if (!sendToRealLine || !lineToken) {
      // Sandboxed Simulation Mode
      setIsSendingToLine(true);
      setTimeout(() => {
        // Append to Simulated Mobile LINE screen
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
        
        const newSimMessage: SimulatedLineMessage = {
          id: `sim_${Date.now()}`,
          sender: 'ai_notify',
          text: textToSend,
          timestamp: timeStr
        };

        setLineChatMessages(prev => [...prev, newSimMessage]);
        
        // Push to History List
        const newHistoryItem: TaskHistory = {
          id: `history_${Date.now()}`,
          command: commandPrompt || "จำลองป้อนข้อความโดยตรง",
          draftMessage: textToSend,
          persona: selectedPersona,
          timestamp: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${timeStr}:${String(now.getSeconds()).padStart(2, '0')}`,
          automationType: agentResult?.automationType || 'simulated',
          targetAudience: agentResult?.targetAudience || 'จำลองส่วนตัว',
          dispatchedToLine: false
        };

        setHistoryList(prev => [newHistoryItem, ...prev]);
        setIsSendingToLine(false);
        showToast('ทดสอบจำลองส่งลง LINE บนหน้าจอจำลองสำเร็จแล้ว! (โหมดแซนด์บอกซ์)', 'success');
      }, 800);
      return;
    }

    // Real API Call via proxy backend
    setIsSendingToLine(true);
    try {
      const response = await fetch('/api/line-notify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: lineToken,
          message: textToSend
        })
      });

      const data = await response.json();

      if (data.success) {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

        // Also add to simulator so user is delighted
        const newSimMessage: SimulatedLineMessage = {
          id: `line_real_${Date.now()}`,
          sender: 'ai_notify',
          text: `[ส่งสำเร็จไปยัง LINE กลุ่มจริง]\n\n${textToSend}`,
          timestamp: timeStr
        };
        setLineChatMessages(prev => [...prev, newSimMessage]);

        // Push to history
        const newHistoryItem: TaskHistory = {
          id: `history_${Date.now()}`,
          command: commandPrompt || "ส่งข้อความจริงไปยังแอปพลิเคชัน LINE",
          draftMessage: textToSend,
          persona: selectedPersona,
          timestamp: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${timeStr}:${String(now.getSeconds()).padStart(2, '0')}`,
          automationType: agentResult?.automationType || 'announcement',
          targetAudience: agentResult?.targetAudience || 'กลุ่มจริง (LINE Notify API)',
          dispatchedToLine: true
        };

        setHistoryList(prev => [newHistoryItem, ...prev]);
        showToast('📢 ส่งข้อความจริงผ่านระบบ LINE Notify API สำเร็จแล้ว!', 'success');
      } else {
        showToast(`ส่งไปจริงไม่สำเร็จ: ${data.error || 'โปรดตรวจสอบความถูกต้องของ Token'}`, 'error');
      }
    } catch (err: any) {
      console.error(err);
      showToast('ไม่สามารถจัดส่งไปยังไลน์ได้เนื่องขัดข้องทางโครงข่ายเครือข่าย', 'error');
    } finally {
      setIsSendingToLine(false);
    }
  };

  // --- Setup Connection Test (Send Simple Hello World to verify user token) ---
  const handleTestToken = async () => {
    if (!lineToken) {
      showToast('กรุณากรอก LINE Notify Token ก่อนกดทดสอบระบบการเชื่อมต่อ', 'error');
      return;
    }

    setIsSendingToLine(true);
    const testMessage = `🎯 [เลขา AI]: ระบบได้ทำการเชื่อมต่อระหว่างเว็บสำเร็จแล้วค่ะ!\nนี่คือข้อความยืนยันการตั้งค่าระบบและจับคู่ Token ของคุณเรียบร้อยแล้ว ยินดีที่ได้เป็นผู้ช่วยทีมงานในการทำงานค่ะ 👩‍💼📱💻`;

    try {
      const response = await fetch('/api/line-notify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: lineToken,
          message: testMessage
        })
      });

      const data = await response.json();
      if (data.success) {
        showToast('🎉 ส่งข้อความทดสอบไปยังกลุ่ม LINE ของคุณเรียบร้อยแล้วค่ะ!', 'success');
      } else {
        showToast(`ทดสอบล้มเหลว: ${data.error || 'Token ไม่ถูกต้อง'}`, 'error');
      }
    } catch (err: any) {
      console.error(err);
      showToast('เกิดข้อผิดพลาดในการเชื่อมต่อเครือข่าย', 'error');
    } finally {
      setIsSendingToLine(false);
    }
  };

  // --- Copy draft message to clipboard ---
  const handleCopyToClipboard = () => {
    const textToCopy = editableDraft || (agentResult ? agentResult.draftMessage : '');
    if (!textToCopy) return;

    navigator.clipboard.writeText(textToCopy);
    showToast('คัดลอกร่างข้อความลงในคลิปบอร์ดแล้ว!', 'success');
  };

  // --- Clear history list ---
  const handleClearHistory = () => {
    if (window.confirm('คุณแน่ใจหรือไม่ที่จะล้างประวัติคำสั่งทั้งหมด?')) {
      setHistoryList([]);
      showToast('ลบประวัติเวิร์กโฟลว์ทั้งหมดแล้ว', 'info');
    }
  };

  // --- Delete single history item ---
  const handleDeleteHistoryItem = (id: string) => {
    setHistoryList(prev => prev.filter(item => item.id !== id));
    showToast('ลบรายการประวัตินี้แล้ว', 'info');
  };

  // --- Load a historical task back into focus ---
  const handleLoadHistory = (item: TaskHistory) => {
    setCommandPrompt(item.command);
    setSelectedPersona(item.persona);
    setEditableDraft(item.draftMessage);
    setAgentResult({
      intent: `โหลดใหม่จากประวัติงาน: ${item.command.slice(0, 30)}...`,
      draftMessage: item.draftMessage,
      automationType: item.automationType,
      targetAudience: item.targetAudience,
      reasoningSteps: [
        "กู้คืนข้อมูลเวิร์กโฟลว์จากประวัติส่วนตัว...",
        "โหลดร่างโครงสร้างดั้งเดิมมาใส่ในตัวควบคุมเสร็จสิ้น"
      ]
    });
    setTerminalLogs([
      `📅 [HISTORY-LOAD]: โหลดประวัติงานบันทึกเวลา ${item.timestamp} สำเร็จ!`,
      "🔎 [REVISION]: คุณสามารถทำการแก้ไขข้อความเพิ่มเติม หรือคลิกแชร์ประกาศลง LINE ได้ทันที"
    ]);
    setActiveLogIndex(1);
    showToast('โหลดโครงร่างข้อความจากประวัติเข้าสู่ตัวแก้ไขแล้วค่ะ!', 'success');
  };

  // Preset commands lists
  const promptPresets = [
    {
      title: "📢 ประกาศฉุกเฉิน / สุภาพ",
      text: "แจ้งเตือนทุกคนในสำนักงานว่าเนื่องจากฝนตกหนัก ค่ำนี้บริเวณลานจอดรถด้านหลังอาจมีน้ำขัง ขอแนะนำให้สลับความระมัดระวังและปิดเครื่องใช้ไฟฟ้าให้เรียบร้อยก่อนกลับ",
      persona: "secretary",
      icon: <Bell className="w-4.5 h-4.5 text-emerald-400" />
    },
    {
      title: "📊 ติดตามความคืบหน้างาน",
      text: "บอกผู้ร่วมโปรเจกต์ทุกคนว่าพรุ่งนี้บ่ายสองจะมีประชุมรีวิวตัวการเดโมระบบ ใครที่ติดงานส่วนหน้าและหลังบ้านช่วยเตรียมสรุปเป็นหัวข้อสั้นคนละ 2 นาทีเสนอด้วยครับ",
      persona: "pm",
      icon: <Briefcase className="w-4.5 h-4.5 text-emerald-400" />
    },
    {
      title: "🔥 ปลุกพลังและแรงใจทีม",
      text: "แต่งคำทักทายสวัสดีตอนเช้าวันพุธเพื่อกระตุ้นพลังบวกในการทำงานให้กับพนักงาน ให้ทีมมีความคิดสร้างสรรค์และลุยทำงานเคียงบ่าเคียงไหล่ร่วมกัน",
      persona: "coach",
      icon: <Lightbulb className="w-4.5 h-4.5 text-emerald-400" />
    },
    {
      title: "🚨 แจ้งระเบียบ / คำเตือนแอดมิน",
      text: "ขอร้องให้พนักงานถอดแอร์และปิดตู้เย็นชั้นวางของทุกครั้งในวันศุกร์ก่อนหยุดเสาร์อาทิตย์ เพื่อประหยัดพลังงานและความปลอดภัยของอารยธรรมส่วนรวม",
      persona: "admin",
      icon: <AlertCircle className="w-4.5 h-4.5 text-emerald-400" />
    }
  ];

  return (
    <div className="min-h-screen bg-[#020617] text-[#f8fafc] font-sans selection:bg-emerald-500/20 antialiased flex flex-col relative transition-colors duration-300">
      
      {/* Background radial soft glows */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-505/5 bg-emerald-500/5 blur-[120px] rounded-full pointer-events-none"></div>
      <div className="absolute bottom-1/4 left-10 w-96 h-96 bg-indigo-500/5 blur-[120px] rounded-full pointer-events-none"></div>

      {/* Sleek Alert / Toast Alert Banner */}
      {toast.message && (
        <div id="custom-toast" className="fixed top-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl bg-slate-900/90 backdrop-blur-xl border border-slate-800 shadow-neon-emerald flex items-center gap-3 animate-fade-in text-sm max-w-md transition-all duration-300">
          {toast.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />}
          {toast.type === 'error' && <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0" />}
          {toast.type === 'info' && <Sparkles className="w-5 h-5 text-teal-400 flex-shrink-0" />}
          <span className="font-semibold text-slate-100">{toast.message}</span>
        </div>
      )}

      {/* --- Header Section (Highly polished dark navigation glass) --- */}
      <header id="app-header" className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-emerald-500 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20 border border-emerald-400/20">
              <Bot className="w-6 h-6 text-slate-950 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-bold tracking-tight text-white">LineAgent Pro</h1>
                <span className="px-2 py-0.5 text-[9px] uppercase font-bold bg-[#06C755]/15 text-[#06C755] border border-[#06C755]/30 rounded-md">
                  Active Realtime
                </span>
              </div>
              <p className="text-xs text-slate-400">เลขา AI ส่วนตัว มอบหมายคำสั่งแทนคุณ แปลงเนื้อหาจัดแต่งอิสระเพื่อแชร์ลงกลุ่ม LINE 👩‍💼📱</p>
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap justify-center">
            <button 
              id="help-btn"
              onClick={() => setIsHelpOpen(!isHelpOpen)}
              className="flex items-center gap-2 px-3.5 py-2 bg-slate-900/60 hover:bg-slate-800/80 text-slate-200 hover:text-white text-xs font-semibold rounded-xl border border-slate-800 transition-all cursor-pointer shadow-sm"
            >
              <HelpCircle className="w-4 h-4 text-emerald-400" />
              <span>แนะนำวิธีสร้าง LINE Token API</span>
            </button>
            <span className="text-slate-800 hidden md:inline">|</span>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/40 rounded-xl border border-slate-800/50">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.7)]"></span>
              <span className="text-[11px] font-mono font-medium text-slate-400">Agent Node Live</span>
            </div>
          </div>

        </div>
      </header>

      {/* --- Main Dashboard Container --- */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 relative z-10">
        
        {/* === Left Column: AI Decision & Input Controls (7 cols) === */}
        <section id="ai-controls-column" className="lg:col-span-7 flex flex-col gap-6">

          {/* Setup Guide Panel (Dark Sleek theme version) */}
          {isHelpOpen && (
            <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 relative animate-fade-in shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 blur-3xl pointer-events-none"></div>
              <button 
                onClick={() => setIsHelpOpen(false)}
                className="absolute top-4 right-4 text-slate-400 hover:text-white bg-slate-800/80 p-1.5 rounded-lg transition-colors cursor-pointer"
              >
                ✕
              </button>
              
              <h3 className="font-bold text-white flex items-center gap-2.5 text-sm mb-4 border-b border-slate-800 pb-2">
                <Settings className="w-5 h-5 text-emerald-400 animate-spin" />
                ทีละขั้นตอน: ลิงก์ระบบ LINE Notify (ฟรี 100%)
              </h3>
              
              <ol className="text-xs text-slate-300 list-decimal list-inside space-y-3 leading-relaxed">
                <li className="pl-1">ลงชื่อเข้าใช้ด้วย ID LINE ของคุณที่เว็บไซต์อย่างเป็นทางการ: <a href="https://notify-bot.line.me/th/" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:text-emerald-300 underline font-semibold inline-flex items-center gap-0.5 ml-1">notify-bot.line.me <ExternalLink className="w-3 h-3" /></a></li>
                <li className="pl-1">เปิดประวัติโปร์ไฟล์มุมขวาบน เลือกหน้า <strong>"หน้าของฉัน (My Page)"</strong></li>
                <li className="pl-1">เลื่อนลงล่างแล้วกดปุ่มสีเขียว <strong>"ออก Token (Generate token)"</strong></li>
                <li className="pl-1">ตั้งชื่อไอคอนผู้ส่ง (เช่น <code>เลขาอัจฉริยะ AI</code>) และ <strong>เลือกแชทส่วนตัว หรือเลือกกลุ่มไลน์</strong> สำหรับรับข้อความ</li>
                <li className="pl-1">เซฟแล้วคัดลอกรหัส Token แถบยาวๆ มากรอกในบานแกน <strong>"การตั้งค่าเชื่อมต่อ LINE"</strong> ด้านล่างขวา</li>
                <li className="pl-1"><strong className="text-emerald-400 font-bold">ขั้นตอนสำคัญที่สุด:</strong> ต้องเชิญสมาชิกร่วมกลุ่มทางการที่มีชื่อว่า <code>LINE Notify</code> เข้าสู่แชทกลุ่มนั้นๆ เสมอ เพื่อให้บอทมีสิทธิ์ยิงข้อความเข้ามา</li>
              </ol>
            </div>
          )}

          {/* AI Task Dispatcher Card (Premium custom glass box) */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 flex flex-col gap-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-[50px] pointer-events-none rounded-full"></div>
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2.5">
                <Sparkles className="w-5 h-5 text-emerald-400 animate-pulse" />
                สั่งการมอบหมายภารกิจ AI
              </h2>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                Autonomous Dispatcher
              </span>
            </div>

            {/* Quick Presets (styled dark) */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5">
                ⚡ ทางลัดคำบอกมอบหมายยอดฮิต (กดเลือกใช้ทันที):
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {promptPresets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleApplyPreset(preset.text, preset.persona)}
                    className="p-3 text-left bg-slate-950/80 hover:bg-slate-900 border border-slate-800/80 hover:border-emerald-500/30 rounded-xl transition-all duration-200 group flex gap-3 cursor-pointer"
                  >
                    <div className="bg-slate-900 p-2 rounded-xl border border-slate-800 group-hover:bg-emerald-950/40 group-hover:border-emerald-800/30 transition-colors flex-shrink-0 flex items-center justify-center">
                      {preset.icon}
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-200 group-hover:text-emerald-400 transition-colors">
                        {preset.title}
                      </div>
                      <p className="text-[10px] text-slate-500 line-clamp-1 mt-1 leading-normal">
                        {preset.text}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Input Form */}
            <form onSubmit={handleRunAgent} className="flex flex-col gap-5">
              <div>
                <label htmlFor="prompt-input" className="block text-xs font-bold text-slate-300 mb-2 flex justify-between">
                  <span>✍️ สั่งข้อความด้วยภาษาพูดของคุณ (ไทย หรือ อังกฤษ):</span>
                  <span className="text-[10px] text-emerald-400 font-bold border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 rounded-md uppercase tracking-wider">
                    Model Server AI
                  </span>
                </label>
                <textarea
                  id="prompt-input"
                  rows={4}
                  value={commandPrompt}
                  onChange={(e) => setCommandPrompt(e.target.value)}
                  placeholder="ตัวอย่างเช่น: 'สั่งให้ทุกคนล้างถ้วยชามและแก้วน้ำของตัวเองในคลังส่วนกลาง ห้ามตั้งแช่ค้างคืนในอ่างลานวัด มิฉะนั้นแอดมินจะเก็บทิ้งทั้งหมดเย็นนี้'"
                  className="w-full text-xs p-4 bg-slate-950 border border-slate-800 rounded-2xl focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 outline-none text-slate-100 placeholder-slate-600 transition-all font-sans leading-relaxed shadow-inner"
                />
              </div>

              {/* Persona Selection (styled sleek dark) */}
              <div>
                <span className="block text-xs font-bold text-slate-300 mb-2.5">
                  👩‍💼 ชนิดบทบาทและน้ำเสียงของเลขา AI:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {[
                    { id: 'secretary', name: 'เลขาฯ สุภาพ', desc: 'อ่อนน้อม สุภาพ นุ่มนวลค่ะ', emoji: '👩‍💼' },
                    { id: 'pm', name: 'ผู้จัดการ PM', desc: 'ทีมลีดเดอร์ ชัดเจน มีข้อบ่งชี้', emoji: '📈' },
                    { id: 'coach', name: 'โค้ชปลุกพลัง', desc: 'สร้างแอนเนอจี้ ให้ความหวัง', emoji: '🔥' },
                    { id: 'admin', name: 'แอดมินระบบ', desc: 'เน้นประกาศฉุกเฉิน ตัวหนา', emoji: '📢' },
                  ].map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setSelectedPersona(p.id)}
                      className={`p-3 rounded-2xl border text-left transition-all duration-200 flex flex-col gap-1.5 cursor-pointer ${
                        selectedPersona === p.id
                          ? 'border-emerald-500 bg-emerald-500/10 shadow-neon-emerald ring-1 ring-emerald-500/30'
                          : 'border-slate-800 bg-slate-950/60 hover:bg-slate-900/80 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-base">{p.emoji}</span>
                        <span className="text-xs font-bold text-slate-100">{p.name}</span>
                      </div>
                      <span className="text-[9px] text-slate-500 line-clamp-1 leading-normal">{p.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit CTA Button with neon glow */}
              <button
                type="submit"
                disabled={isAnalyzing || !commandPrompt.trim()}
                className="w-full py-3.5 px-4 bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed disabled:shadow-none text-slate-950 rounded-2xl font-bold flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-neon-emerald-strong transition-all duration-300 cursor-pointer text-xs uppercase tracking-wider"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>กำลังวิเคราะห์ถอดโค้ดสรุปงาน...</span>
                  </>
                ) : (
                  <>
                    <Bot className="w-5 h-5 text-slate-950 animate-pulse" />
                    <span>⚡ สั่งการเลขา AI ไปทำงานแทนคุณ</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* AI Executive Steps Panel (Continuous workflow display) */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-3xl shadow-xl overflow-hidden backdrop-blur-md">
            <div className="bg-slate-950/80 px-4 py-3 flex justify-between items-center border-b border-slate-850">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
                <span className="text-xs font-bold font-mono text-emerald-400 uppercase tracking-widest">Thought process logs</span>
              </div>
              <span className="text-[10px] font-mono text-slate-600">LIVE_AGENT_STREAM</span>
            </div>
            
            <div className="p-4 font-mono text-[11px] text-emerald-300 space-y-2 min-h-36 max-h-56 overflow-y-auto bg-slate-950/20 leading-relaxed scrollbar-thin">
              {terminalLogs.length === 0 ? (
                <div className="text-slate-500 text-center py-6">
                  <span>[AGENT_SYSTEM]: โหมดพร้อมประมวลผล สแตนด์บายคำสั่งร่างประกาศถัดไป...</span>
                  <p className="text-[10px] mt-2 text-slate-600">วิเคราะห์ ลำดับการประมวลผล และข้อความสังเคราะห์เดโมจะเด้งที่นี่แบบนาทีต่อนาที</p>
                </div>
              ) : (
                terminalLogs.map((log, index) => (
                  <div 
                    key={index} 
                    className={`transition-all duration-200 ${
                      index === activeLogIndex ? 'text-white border-l-2 border-emerald-400 pl-3 bg-emerald-500/5 py-0.5' : 'opacity-60'
                    }`}
                  >
                    {log}
                  </div>
                ))
              )}
            </div>

            {/* Prompt Meta Results */}
            {agentResult && (
              <div className="bg-slate-950/70 px-4 py-3.5 border-t border-slate-850 grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-400">
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-600 text-[9px] uppercase font-bold">ประเภทงาน:</span>
                  <span className="text-emerald-400 font-semibold">{agentResult.automationType?.toUpperCase() || '-'}</span>
                </div>
                <div className="flex flex-col gap-0.5 overflow-hidden">
                  <span className="text-slate-600 text-[9px] uppercase font-bold">กลุ่มเป้าหมาย:</span>
                  <span className="text-blue-400 font-semibold truncate block" title={agentResult.targetAudience}>
                    {agentResult.targetAudience || 'ทั่วไป'}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-600 text-[9px] uppercase font-bold">กำหนดสเกลเลอร์:</span>
                  <span className="text-amber-400 font-semibold">{agentResult.scheduleTime || 'โพสต์ทันที'}</span>
                </div>
              </div>
            )}
          </div>

          {/* Local Task Automations History Column */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 flex flex-col gap-4 shadow-xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-bold text-sm text-white">📅 โครงสร้างผลงานบันทึกประวัติ</h3>
                <p className="text-[10px] text-slate-500 mt-0.5">เวิร์กโฟลว์จัดแต่งข้อความของเลขาที่บันทึกสำรองในเบราว์เซอร์ส่วนตัว</p>
              </div>
              {historyList.length > 0 && (
                <button
                  onClick={handleClearHistory}
                  className="p-1 px-2.5 hover:bg-rose-950/35 text-[10px] text-rose-400 font-bold rounded-lg transition-colors border border-slate-800 hover:border-rose-900/50 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 inline mr-1" />
                  ล้างประวัติ
                </button>
              )}
            </div>

            {historyList.length === 0 ? (
              <div className="text-center py-8 text-slate-650 text-xs text-slate-500">
                ยังไม่มีข้อมูลประวัติการร่างงานในปัจจุบัน
              </div>
            ) : (
              <div className="space-y-3.5 max-h-80 overflow-y-auto pr-1 select-none">
                {historyList.map((item) => (
                  <div 
                    key={item.id}
                    className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-2xl flex items-start justify-between gap-3 hover:border-slate-700 transition-all duration-200 group relative"
                  >
                    <div className="flex-grow space-y-2.5">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider ${
                          item.persona === 'secretary' ? 'bg-indigo-950 text-indigo-300 border border-indigo-905/30' :
                          item.persona === 'pm' ? 'bg-blue-950 text-blue-300 border border-blue-905/30' :
                          item.persona === 'coach' ? 'bg-amber-950 text-amber-300 border border-amber-905/30' :
                          'bg-rose-950 text-rose-300 border border-rose-905/30'
                        }`}>
                          {item.persona === 'secretary' ? '👩‍💼 เลขาสุภาพ' :
                           item.persona === 'pm' ? '📈 ผู้ควบคุมโปรเจกต์' :
                           item.persona === 'coach' ? '🔥 โค้ชสร้างแรงพลัง' :
                           '📢 แอดมินระบบ'}
                        </span>

                        <span className="text-[10px] font-mono text-slate-500">
                          {item.timestamp}
                        </span>

                        {item.dispatchedToLine ? (
                          <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded-md border border-emerald-900/50">
                            ✓ ส่งสำเร็จ LINE จริง
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-slate-400 bg-slate-900/80 px-2 py-0.5 rounded-md border border-slate-800">
                            ⚙️ แซนด์บอกซ์จำลอง
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        <span className="block text-xs font-semibold text-slate-100 line-clamp-1">{item.command}</span>
                        <p className="text-[11px] text-slate-400 line-clamp-2 bg-slate-900/20 p-2.5 rounded-xl border border-slate-800/50 italic leading-relaxed">
                          {item.draftMessage}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 items-end flex-shrink-0 self-center">
                      <button
                        onClick={() => handleLoadHistory(item)}
                        className="px-2.5 py-1.5 text-[10px] font-bold bg-slate-900 hover:bg-emerald-500 border border-slate-800 hover:border-emerald-500 text-slate-300 hover:text-slate-950 rounded-lg shadow-sm hover:shadow-neon-emerald transition-all duration-200 flex items-center gap-1 cursor-pointer"
                      >
                        <RefreshCw className="w-3 h-3" />
                        ดึงงานคืน
                      </button>
                      <button
                        onClick={() => handleDeleteHistoryItem(item.id)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-rose-950/20 transition-colors cursor-pointer"
                        title="ลบรายการนี้"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* === Right Column: Result Playground & Interactive LINE Emulator === */}
        <section id="result-visual-column" className="lg:col-span-5 flex flex-col gap-6">
          
          {/* Editor Playground Card */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm text-slate-100">📝 กล่องขัดเกลาและแก้ไขข้อความ</h3>
              </div>
              {agentResult && (
                <button
                  onClick={handleCopyToClipboard}
                  className="text-xs text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1.5 cursor-pointer bg-emerald-500/10 hover:bg-emerald-500/20 px-2 py-1 rounded-lg border border-emerald-500/20 transition-all duration-200"
                >
                  <Clipboard className="w-3.5 h-3.5" />
                  คัดลอกร่าง
                </button>
              )}
            </div>

            {agentResult ? (
              <div className="space-y-4">
                <div className="p-3.5 bg-emerald-950/25 border border-emerald-900/40 rounded-2xl text-xs text-slate-300 leading-relaxed shadow-inner">
                  <span className="font-bold text-white flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    วิเคราะห์เป้าหมายเปรียบต่าง:
                  </span>
                  <div className="font-sans">
                    <span className="text-slate-400 italic">" {agentResult.intent} "</span>
                  </div>
                </div>

                <div>
                  <label htmlFor="draft-editor" className="block text-xs font-bold text-slate-400 mb-2">
                    คุณสามารถปรับเปลี่ยนเนื้อหาข้อความ หรืออัพเดทได้อย่างอิสระ:
                  </label>
                  <textarea
                    id="draft-editor"
                    rows={8}
                    value={editableDraft}
                    onChange={(e) => setEditableDraft(e.target.value)}
                    className="w-full text-xs p-4 bg-slate-950 border border-slate-800 rounded-2xl focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none text-slate-100 font-mono leading-relaxed"
                  />
                </div>

                {/* Dispatch to Line Actions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 border-t border-slate-800 pt-3">
                  <div className="flex flex-col justify-center">
                    <span className="text-[9px] text-slate-500 uppercase tracking-widest font-bold">สถานะการทำงานตอนนี:</span>
                    <span className={`text-xs font-bold mt-0.5 ${sendToRealLine && lineToken ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {sendToRealLine && lineToken ? '📢 พร้อมเผยแพร่ LINE กลุ่มจริง' : '⚙️ โหมดจำลองผลทดสอบภายใน'}
                    </span>
                  </div>
                  
                  <button
                    onClick={handleDispatchToLine}
                    disabled={isSendingToLine || !editableDraft.trim()}
                    className="py-3 px-4 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-slate-950 text-xs font-bold rounded-xl shadow-md hover:shadow-neon-emerald transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {isSendingToLine ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>กำลังจัดส่ง...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span>โพสต์เผยแพร่เข้า LINE ทันที</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 bg-slate-950/40 rounded-2xl border border-dashed border-slate-800 space-y-3.5">
                <div className="w-12 h-12 bg-slate-900 border border-slate-800 rounded-full flex items-center justify-center mx-auto shadow-sm">
                  <Bot className="w-6 h-6 text-slate-600 animate-pulse" />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-400 block">ยังไม่มีแผนสังเคราะห์ผลลัพธ์</span>
                  <p className="text-[10px] text-slate-500 max-w-xs mx-auto px-4 mt-1.5 leading-relaxed">
                    โปรดระบุหน้าที่หรือเป้าหมายที่ต้องการด้านซ้ายแผงควบคุม แล้วกดมอบหมายงาน บอทจะเริ่มสังเคราะห์และแก้ไขขัดเกลาเนื้อหาโชว์ตรงนี้ค่ะ
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Interactive Mobile Emulator - Custom LINE Dark/Space Simulator */}
          <div className="bg-[#090d16] rounded-[38px] border-[8px] border-slate-950 shadow-2xl overflow-hidden flex flex-col h-[520px] relative border-b-[12px] border-t-[10px]">
            
            {/* Phone Top Speaker & Notch */}
            <div className="bg-slate-950 px-6 pt-2 pb-1.5 flex justify-between items-center text-slate-500 text-[8px] font-semibold flex-shrink-0">
              <span className="font-mono">12:12 PM</span>
              <div className="w-16 h-3 bg-slate-900 rounded-full border border-slate-800 flex items-center justify-center">
                <span className="w-1 h-1 bg-blue-500 rounded-full block"></span>
              </div>
              <div className="flex items-center gap-1 font-mono">
                <span>LINE SIM</span>
                <span className="text-[7px] bg-slate-800 px-1 rounded text-emerald-400">5G</span>
              </div>
            </div>

            {/* Simulated LINE Header with original deep green aesthetic */}
            <div className="bg-slate-900 px-4 py-3 flex items-center gap-3 border-b border-slate-950 flex-shrink-0">
              <div className="relative">
                <div className="w-9 h-9 bg-emerald-500 text-slate-950 font-bold rounded-2xl flex items-center justify-center text-xs shadow-md border border-emerald-400/20">
                  LN
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-slate-900"></span>
              </div>
              <div className="flex-grow">
                <span className="block text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  LINE Notify (AI Secretarial Sandbox)
                  <span className="bg-[#06C755]/15 text-[#06C755] border border-[#06C755]/30 text-[7px] px-1.5 py-0.5 rounded-md font-mono uppercase tracking-wider font-semibold">
                    CONNECTED
                  </span>
                </span>
                <p className="text-[9px] text-slate-450 text-slate-400">ระบบจำลองพฤติกรรมบอทไลน์และการทดสอบส่งข้อมูล</p>
              </div>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
              </div>
            </div>

            {/* Simulated Chat Feed (Line Custom Sleek Dark Grayish Blue Background) */}
            <div className="flex-grow bg-[#0f172a] p-4 overflow-y-auto space-y-4 text-xs font-sans scrollbar-thin">
              <div className="text-center">
                <span className="bg-slate-900/80 border border-slate-800 text-slate-400 text-[8px] py-1 px-2.5 rounded-full uppercase tracking-wider font-semibold font-mono">
                  🚨 FEED SIMULATION CONTAINER
                </span>
              </div>

              {lineChatMessages.map((msg) => (
                <div key={msg.id} className="flex gap-2.5 items-start">
                  {/* Sender Avatar */}
                  <div className="w-8 h-8 bg-emerald-500 rounded-xl text-[10px] text-slate-950 font-bold flex items-center justify-center shadow-md flex-shrink-0 mt-0.5">
                    LN
                  </div>

                  {/* Bubble Container */}
                  <div className="max-w-[82%] flex flex-col gap-1">
                    <span className="text-[9px] text-slate-400 font-bold ml-1.5 flex items-center gap-1">
                      LINE Notify Bot <span className="text-[8px] text-slate-500 font-normal">แชร์เมื่อ {msg.timestamp}</span>
                    </span>
                    <div className="relative bg-slate-900 text-slate-100 p-3.5 rounded-2xl rounded-tl-sm shadow-md border border-slate-800/80 whitespace-pre-wrap leading-relaxed text-xs">
                      {msg.text}
                    </div>
                  </div>
                </div>
              ))}

              <div ref={chatBottomRef} />
            </div>

            {/* Phone bottom bar mockup */}
            <div className="bg-slate-950 p-2.5 flex justify-center items-center flex-shrink-0 border-t border-slate-900">
              <div className="w-24 h-1 bg-slate-800 rounded-full"></div>
            </div>
          </div>

          {/* Real Token Setup Configuration (Persistent storage client-side) */}
          <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Settings className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-sm text-slate-100 font-sans">🔌 การตั้งค่าเชื่อมต่อระบบ LINE จริง</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="token-input" className="block text-xs font-bold text-slate-400 mb-2 flex justify-between">
                  <span>🔑 LINE Notify Token รับสิทธิ์ลงโพสต์:</span>
                  <button 
                    onClick={() => setIsHelpOpen(!isHelpOpen)}
                    type="button" 
                    className="text-emerald-400 hover:underline hover:text-emerald-300 text-[10px] bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md cursor-pointer font-semibold uppercase tracking-wider"
                  >
                    วิธีการหา Token?
                  </button>
                </label>
                <div className="relative">
                  <input
                    id="token-input"
                    type="password"
                    value={lineToken}
                    onChange={(e) => setLineToken(e.target.value)}
                    placeholder="กรอกรหัส Token (เช่น eX7Yp894...) ที่ได้จากเว็บเซถ็นเพื่อโพสต์จริง"
                    className="w-full text-xs p-3.5 bg-slate-950 border border-slate-800 rounded-xl focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 outline-none pr-12 text-slate-100 font-mono shadow-inner placeholder-slate-600"
                  />
                  {lineToken && (
                    <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[9px] uppercase font-bold text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded border border-emerald-500/30">
                      ✓ CONNECTED
                    </span>
                  )}
                </div>
              </div>

              {/* Destination Switcher */}
              <div className="p-3.5 bg-slate-950 border border-slate-850 rounded-2xl flex items-center justify-between gap-4">
                <div className="space-y-0.5 flex-grow">
                  <span className="block text-xs font-bold text-slate-200">เผยแพร่ข้อมูลตรงไปยังไลน์กลุ่มผู้ใช้?</span>
                  <p className="text-[10px] text-slate-500 leading-normal">
                    หากสลับเปิด บอทจะทำการส่งข้อความประกาศจริงไปยังไลน์ผ่าน API (หากปิดไว้จะทดสอบแช่งฉายเดโมเฉพาะหน้าจอจำลองด้านบนเท่านั้น)
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setSendToRealLine(!sendToRealLine)}
                  className={`w-12 h-6.5 rounded-full p-1 transition-colors duration-200 flex items-center cursor-pointer flex-shrink-0 ${
                    sendToRealLine && lineToken ? 'bg-emerald-500 justify-end' : 'bg-slate-800 justify-start'
                  }`}
                >
                  <span className={`w-4.5 h-4.5 bg-white rounded-full shadow-sm transition-transform duration-100 ${sendToRealLine && lineToken ? 'bg-slate-950' : 'bg-slate-300'}`}></span>
                </button>
              </div>

              {/* Action connection test */}
              {lineToken && (
                <button
                  type="button"
                  onClick={handleTestToken}
                  disabled={isSendingToLine}
                  className="w-full py-2.5 bg-slate-950 hover:bg-slate-950/40 text-slate-300 hover:text-white border border-slate-800 text-xs font-bold rounded-xl shadow-sm hover:shadow-neon-emerald transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                  <span>⚡ ส่งข้อความทักทายทดสอบสิทธิ์ Token เข้าแชท LINE จริง</span>
                </button>
              )}
            </div>
          </div>
        </section>

      </main>

      {/* --- Footer bar --- */}
      <footer className="bg-slate-950 border-t border-slate-900 py-6 px-6 text-center text-xs text-slate-500 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <span>© 12:12:16 LINE AI Secretarial Agent Pro. พลังประมวลเก่งกล้าผ่าน Gemini และ Express Server Node Proxy</span>
          <div className="flex gap-4">
            <span className="font-semibold text-slate-450 hover:text-white transition-colors">ล้างข้อมูลเมื่อปิดบราวเซอร์</span>
            <span>|</span>
            <span className="font-semibold text-slate-450 hover:text-white transition-colors">LINE Notify API Verified Ready</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
