import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI, Type } from '@google/genai';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Path resolution safe for both ESM (tsx dev mode) and CJS (bundled by esbuild)
const getPaths = () => {
  try {
    if (typeof __filename !== 'undefined' && typeof __dirname !== 'undefined') {
      return { filename: __filename, dirname: __dirname };
    }
  } catch (e) {}

  const filename = fileURLToPath(import.meta.url);
  const dirname = path.dirname(filename);
  return { filename, dirname };
};

const { filename: activeFilename, dirname: activeDirname } = getPaths();

// Initialize Gemini SDK with telemetry header
const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.warn("WARNING: GEMINI_API_KEY environment variable is not defined");
}

const ai = new GoogleGenAI({
  apiKey: apiKey || '',
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    }
  }
});

async function startServer() {
  const app = express();
  app.use(express.json());

  // 1. API: LINE Notify Proxy (Bypasses browser CORS restriction)
  app.post('/api/line-notify', async (req, res) => {
    const { token, message } = req.body;

    if (!token) {
      return res.status(400).json({ success: false, error: 'LINE Notify Token is required' });
    }
    if (!message) {
      return res.status(400).json({ success: false, error: 'Message content is required' });
    }

    try {
      console.log('Sending notification via LINE Notify API to LINE group/user...');
      
      const response = await fetch('https://notify-api.line.me/api/notify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}`
        },
        body: new URLSearchParams({ message })
      });

      const data = await response.json();

      if (response.ok && data.status === 200) {
        return res.json({ success: true, message: 'Message successfully sent to LINE!' });
      } else {
        return res.status(400).json({ 
          success: false, 
          error: data.message || 'Failed to dispatch notification to LINE Notify API.' 
        });
      }
    } catch (err: any) {
      console.error('Error calling LINE Notify API:', err);
      return res.status(500).json({ 
        success: false, 
        error: err.message || 'Internal Server Error' 
      });
    }
  });

  // 2. API: AI Secretarial Agent endpoint runs server-side Gemini
  app.post('/api/agent/run', async (req, res) => {
    const { prompt, agentPersona, lineToken } = req.body;

    if (!prompt) {
      return res.status(400).json({ success: false, error: 'Goal prompt is required' });
    }

    const personaDescriptions: Record<string, string> = {
      secretary: 'เลขาฯ มืออาชีพ สุภาพ เรียบร้อย ละเอียดรอบคอบ และคอยดูแลตารางงานได้ไร้ที่ติ',
      pm: 'ผู้ช่วยผู้จัดการโครงการ (Project Manager) เน้นความชัดเจน แบ่งงานเป็นขั้นตอน และติดตามความคืบหน้าอย่างเป็นระบบ',
      coach: 'โค้ชสร้างแรงบันดาลใจ (Motivational Coach) ใช้คำพูดเติมพลังบวก กระตุ้นทีม และเปี่ยมไปด้วยพลังขับเคลื่อน',
      admin: 'ผู้ดูแลระบบและประกาศด่วน (System Co-ordinator) ชัดเจน กระชับ ตรงประเด็น ใช้ประกาศแจ้งข่าวสารด่วน',
    };

    const selectedPersona = personaDescriptions[agentPersona] || personaDescriptions.secretary;

    try {
      console.log(`Analyzing instruction using Gemini: "${prompt}" (Persona: ${agentPersona})`);

      // Define the structured schema we expect from Gemini
      const responseSchema = {
        type: Type.OBJECT,
        properties: {
          intent: {
            type: Type.STRING,
            description: "สรุปเป้าหมายหรือความต้องการของผู้ใช้ในประโยคสั้นๆ",
          },
          reasoningSteps: {
            type: Type.ARRAY,
            items: { type: Type.STRING },
            description: "ลำดับขั้นตอนการทำงานของผู้ใช้นี้ (3-4 ขั้นตอนภาษาไทย) เช่น วิเคราะห์เนื้อหา, ร่างประโยค, จัดแต่งความสวยงาม",
          },
          draftMessage: {
            type: Type.STRING,
            description: "ร่างข้อความที่จะส่งลงไลน์ ออกแบบและจัดรูปแบบอย่างสวยงาม จัดย่อหน้า ใช้กระสุนนำ (bullet points) เว้นวรรคอย่างเหมาะสม และมีอิโมจิ (emojis) ตกแต่งอย่างเหมาะสม ดูเป็นมืออาชีพ มีความสุภาพ",
          },
          automationType: {
            type: Type.STRING,
            description: "ประเภทของการเตือนภัยหรือแอปพลิเคชัน: announcement, reminder, todo หรือ creative",
          },
          scheduleTime: {
            type: Type.STRING,
            description: "รายละเอียดวันเวลาหากเป็นสิ่งที่ต้องกำหนดตารางเวลา (เช่น ทุกเช้าวันจันทร์ 9:00 น., 25 พ.ค. 14:00 น.) หากไม่มีให้ปล่อยว่าง",
          },
          targetAudience: {
            type: Type.STRING,
            description: "คำอธิบายกลุ่มเป้าหมายผู้รับสาร เช่น กลุ่มเพื่อนร่วมงาน, กลุ่มครอบครัว หรือสำหรับการแจ้งเตือนส่วนตัว",
          }
        },
        required: ["intent", "reasoningSteps", "draftMessage", "automationType", "targetAudience"],
      };

      const systemInstruction = `คุณคือ "LINE AI Secretarial Agent" (เลขา AI ส่วนตัว).
หน้าที่ของคุณคือรับคำสั่งจากผู้ใช้เพื่อสั่งงาน เขียนประกาศ แต่งโพสต์ ตั้งเตือน หรือสรุปข้อความ เพื่อนำมาโพสต์หรือส่งแจ้งเตือนในระบบ LINE ของผู้ใช้
บุคลิกหลักของคุณคือ: ${selectedPersona}

กรุณาทำความเข้าใจเจตจำนงของผู้ใช้อย่างละเอียด และสร้างสรรค์ข้อความที่:
1. ภาษาไทยธรรมชาติ สุภาพ เรียบร้อย น่าอ่าน เหมาะสมกับบุคลิกที่เลือก
2. จัดวางหน้าอย่างประณีต มีหัวข้อหลัก มีจุดกระสุนนำ (bullet points) ย่อหน้า และช่องว่างสายตาที่ดี
3. มีการใช้อิโมจิสอดคล้องกับเนื้อความอย่างมีศิลปะ ไม่รกรุงรัง แต่ดึงดูดสายตา
4. มีข้อมูลครบถ้วนตามที่ร้องขอ

คุณต้องส่งผลลัพธ์กลับมาในรูปแบบ JSON ตาม Schema ที่กำหนดให้เท่านั้น`;

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: prompt,
        config: {
          systemInstruction,
          responseMimeType: "application/json",
          responseSchema,
          temperature: 0.7,
        },
      });

      const responseText = response.text;
      if (!responseText) {
        throw new Error('No response text retrieved from Gemini Model.');
      }

      const agentResult = JSON.parse(responseText.trim());

      return res.json({
        success: true,
        agentResult,
      });

    } catch (err: any) {
      console.error('Gemini execution error:', err);
      return res.status(500).json({ 
        success: false, 
        error: err.message || 'Failed to analyze task with AI agent.' 
      });
    }
  });

  // 3. SPA Handlers & Dev Server Setup
  if (process.env.NODE_ENV !== 'production') {
    console.log('Mounting Vite dev server middleware in Express...');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    console.log('Serving production static build files from dist...');
    app.use(express.static(path.resolve(activeDirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(activeDirname, 'dist/index.html'));
    });
  }

  // 4. Start the server on port 3000 (Required by infra, listening on 0.0.0.0)
  const port = 3000;
  app.listen(port, '0.0.0.0', () => {
    console.log(`🚀 AI Secretarial Agent App Server now running on http://0.0.0.0:${port}`);
  });
}

startServer().catch((err) => {
  console.error('Fatal server start error:', err);
});
