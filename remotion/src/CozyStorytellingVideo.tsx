import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Scene structure: context line + big punchy kinetic badge
export interface SceneData {
  startFrame: number;
  endFrame: number;
  badge: string;
  leadWords: { text: string; start: number; end: number }[];
  keyPhrase: {
    text: string;
    start: number;
    end: number;
    pillBg: string;
    textColor: string;
    icon: string;
  };
  note: {
    title: string;
    body: string;
    color: string;
    tag: string;
    rotation: number;
  };
  characterState: "reflecting" | "loyal" | "sad" | "peace" | "regret" | "proud";
  action?: "idle" | "think" | "walk" | "nod" | "shake_head" | "heart" | "celebrate" | "breathe" | "release" | "reach" | "embrace" | "point" | "choose" | "water" | "rise" | "turn_away";
  visual?: "parting" | "support" | "burden" | "crossroads" | "growth" | "journey" | "conversation" | "reflection" | "celebration" | "peace";
  actionStart?: number;
}

export interface CozyStorytellingProps {
  [key: string]: unknown;
  scenes?: SceneData[];
  audioSrc?: string;
  totalDurationInFrames?: number;
  channelTag?: string;
  aspectRatio?: string;
  style?: string; // "cozy" | "midnight" | "scrapbook" | "pixel" | "brutalism" | "whiteboard"
  character?: string; // "stickman" | "cat" | "hoodie" | "bear" | "bot" | "ghost"
  width?: number;
  height?: number;
  timedDialogue?: boolean;
}

const SCENES: SceneData[] = [
  {
    startFrame: 0,
    endFrame: 96,
    badge: "⚖️ QUY LUẬT CUỘC SỐNG",
    leadWords: [
      { text: "Mọi", start: 3, end: 12 },
      { text: "thứ", start: 12, end: 20 },
      { text: "trên", start: 20, end: 27 },
      { text: "đời", start: 27, end: 35 },
      { text: "này", start: 35, end: 42 },
      { text: "đều", start: 42, end: 50 },
      { text: "có", start: 50, end: 58 },
    ],
    keyPhrase: {
      text: "NHÂN QUẢ",
      start: 58,
      end: 96,
      pillBg: "#E07A5F",
      textColor: "#FFFFFF",
      icon: "⚖️",
    },
    note: {
      title: "⚖️ NHÂN QUẢ",
      body: "Mọi việc trên đời này\nđều có nguyên do & nhân quả.",
      color: "#FFF3B0",
      tag: "Gieo gì gặt nấy",
      rotation: -3,
    },
    characterState: "reflecting",
  },
  {
    startFrame: 96,
    endFrame: 156,
    badge: "🔒 BẢN LĨNH TÌNH YÊU",
    leadWords: [
      { text: "Cách", start: 96, end: 104 },
      { text: "duy", start: 104, end: 110 },
      { text: "nhất", start: 110, end: 116 },
      { text: "bảo", start: 116, end: 122 },
      { text: "vệ", start: 122, end: 128 },
      { text: "tình", start: 128, end: 133 },
      { text: "duyên", start: 133, end: 138 },
      { text: "là", start: 138, end: 142 },
    ],
    keyPhrase: {
      text: "CHUNG THỦY ĐẾN CÙNG",
      start: 142,
      end: 156,
      pillBg: "#3D405B",
      textColor: "#FFFFFF",
      icon: "🔒",
    },
    note: {
      title: "🔒 CHUNG THỦY",
      body: "Cách duy nhất bảo vệ tình yêu\nlà chung thủy đến tận cùng.",
      color: "#FFE5D9",
      tag: "Trọn vẹn một lòng",
      rotation: 2.5,
    },
    characterState: "loyal",
  },
  {
    startFrame: 156,
    endFrame: 210,
    badge: "🌱 DÙ KHÔNG ĐÁP LẠI",
    leadWords: [
      { text: "Nếu", start: 156, end: 164 },
      { text: "lòng", start: 164, end: 172 },
      { text: "chung", start: 172, end: 180 },
      { text: "thủy", start: 180, end: 188 },
      { text: "không", start: 188, end: 196 },
      { text: "đổi", start: 196, end: 202 },
      { text: "được", start: 202, end: 206 },
    ],
    keyPhrase: {
      text: "SỰ CHÂN THÀNH",
      start: 206,
      end: 210,
      pillBg: "#E76F51",
      textColor: "#FFFFFF",
      icon: "💔",
    },
    note: {
      title: "🌱 CHÂN THÀNH",
      body: "Dù chung thủy không đổi lại\nđược sự chân thành...",
      color: "#D8E2DC",
      tag: "Đừng vội nản lòng",
      rotation: -2,
    },
    characterState: "sad",
  },
  {
    startFrame: 210,
    endFrame: 270,
    badge: "✨ BÌNH YÊN TRONG TÂM",
    leadWords: [
      { text: "Thì", start: 210, end: 218 },
      { text: "ít", start: 218, end: 226 },
      { text: "nhất", start: 226, end: 234 },
      { text: "nó", start: 234, end: 242 },
      { text: "cũng", start: 242, end: 248 },
      { text: "cho", start: 248, end: 254 },
      { text: "ta", start: 254, end: 258 },
    ],
    keyPhrase: {
      text: "LƯƠNG TÂM SẠCH SẼ",
      start: 258,
      end: 270,
      pillBg: "#2A9D8F",
      textColor: "#FFFFFF",
      icon: "✨",
    },
    note: {
      title: "✨ LƯƠNG TÂM",
      body: "Ít nhất nó cũng cho ta\nmột lương tâm sạch sẽ & thanh thản.",
      color: "#E2ECE9",
      tag: "Thanh thản trong tâm",
      rotation: 3,
    },
    characterState: "peace",
  },
  {
    startFrame: 270,
    endFrame: 342,
    badge: "🌿 VỮNG LÒNG TIN",
    leadWords: [
      { text: "Người", start: 270, end: 278 },
      { text: "tử", start: 278, end: 286 },
      { text: "tế", start: 286, end: 294 },
      { text: "có", start: 294, end: 300 },
      { text: "thể", start: 300, end: 306 },
      { text: "buồn", start: 306, end: 314 },
      { text: "vì", start: 314, end: 320 },
    ],
    keyPhrase: {
      text: "CHƯA ĐƯỢC CÔNG NHẬN",
      start: 320,
      end: 342,
      pillBg: "#F4A261",
      textColor: "#FFFFFF",
      icon: "🌿",
    },
    note: {
      title: "🌿 NGƯỜI TỬ TẾ",
      body: "Có thể buồn vì đối xử tốt\nmà chưa được công nhận...",
      color: "#FDE2E4",
      tag: "Vững vàng bước tiếp",
      rotation: -2.5,
    },
    characterState: "reflecting",
  },
  {
    startFrame: 342,
    endFrame: 396,
    badge: "⚡ QUY LUẬT BÙ TRỪ",
    leadWords: [
      { text: "Nhưng", start: 342, end: 350 },
      { text: "kẻ", start: 350, end: 358 },
      { text: "bội", start: 358, end: 366 },
      { text: "bạc", start: 366, end: 374 },
      { text: "sẽ", start: 374, end: 380 },
      { text: "phải", start: 380, end: 384 },
    ],
    keyPhrase: {
      text: "HỐI HẬN CẢ ĐỜI!",
      start: 384,
      end: 396,
      pillBg: "#E63946",
      textColor: "#FFFFFF",
      icon: "⚡",
    },
    note: {
      title: "⚡ HỐI HẬN",
      body: "Kẻ bội bạc & phản bội\nsẽ hối hận cả đời!",
      color: "#FFCAD4",
      tag: "Nhân quả báo ứng",
      rotation: 2.8,
    },
    characterState: "regret",
  },
  {
    startFrame: 396,
    endFrame: 448,
    badge: "🌟 TRỌN VẸN MỘT ĐỜI",
    leadWords: [
      { text: "Hãy", start: 396, end: 404 },
      { text: "sống", start: 404, end: 412 },
      { text: "tử", start: 412, end: 420 },
      { text: "tế", start: 420, end: 428 },
      { text: "để", start: 428, end: 434 },
      { text: "khi", start: 434, end: 440 },
    ],
    keyPhrase: {
      text: "NHÌN LẠI KHÔNG THẸN ✨",
      start: 440,
      end: 448,
      pillBg: "#1D3557",
      textColor: "#FFFFFF",
      icon: "🌟",
    },
    note: {
      title: "🌟 TRỌN VẸN",
      body: "Sống tử tế để khi ngoảnh lại,\nta không thẹn với chính mình.",
      color: "#D8E2DC",
      tag: "Tâm an vạn sự an",
      rotation: -1.5,
    },
    characterState: "proud",
  },
];

// Helper: Get styling theme configuration
function getTheme(styleName: string) {
  const s = (styleName || "cozy").toLowerCase();
  switch (s) {
    case "midnight":
      return {
        id: "midnight",
        fontFamily: "'Playfair Display', Georgia, 'Times New Roman', serif",
        bg: "radial-gradient(ellipse at 50% 25%, #182032 0%, #0D111A 65%, #06080D 100%)",
        grid: "radial-gradient(rgba(244, 226, 187, 0.08) 1px, transparent 1px)",
        gridSize: "36px 36px",
        headerBg: "rgba(22, 28, 42, 0.88)",
        headerBorder: "1.5px solid rgba(244, 226, 187, 0.4)",
        headerTextColor: "#F4E2BB",
        headerIcon: "✦",
        headerShadow: "0 8px 30px rgba(0,0,0,0.6)",
        headerRadius: 30,
        cardBg: () => "rgba(18, 24, 38, 0.94)",
        cardBorder: "1.5px solid rgba(244, 226, 187, 0.45)",
        cardShadow: "0 22px 55px rgba(0,0,0,0.85), inset 0 1px 0 rgba(255,255,255,0.12)",
        cardRadius: 16,
        cardTitleColor: "#F4E2BB",
        cardTagBg: "rgba(244, 226, 187, 0.15)",
        cardTagColor: "#F4E2BB",
        cardBodyColor: "#E2E8F0",
        cardDivider: "1px solid rgba(244, 226, 187, 0.22)",
        cardTapeBg: "rgba(244, 226, 187, 0.28)",
        leadActiveColor: "#FFF4D4",
        leadActiveBg: undefined as string | undefined,
        leadActiveBorder: undefined as string | undefined,
        leadActivePadding: undefined as string | undefined,
        leadActiveRadius: undefined as number | string | undefined,
        leadActiveShadow: "0 0 25px rgba(244, 226, 187, 0.9), 0 0 50px rgba(244, 162, 97, 0.5)",
        leadActiveScale: 1.35,
        leadPastColor: "#E2E8F0",
        leadFutureColor: "rgba(148, 163, 184, 0.32)",
        keyShadow: "0 16px 45px rgba(244, 226, 187, 0.35)",
        keyBorder: "2px solid #F4E2BB",
        keyRadius: 36,
        eqColors: ["#F4E2BB", "#38BDF8", "#F4A261"],
        eqShadow: "0 0 14px rgba(244, 226, 187, 0.65)",
        eqRadius: 3,
        charStroke: "#F4E2BB",
        charStrokeWidth: 6,
        charHeadFill: "#141926",
        charHeadFilter: "drop-shadow(0 0 14px rgba(244, 226, 187, 0.65))",
        charBlushColor: "rgba(244, 226, 187, 0.25)",
        charScarfFill: "#D97706",
        charScarfStroke: "#F4E2BB",
        charMouthFill: "#F4E2BB",
      };

    case "scrapbook":
      return {
        id: "scrapbook",
        fontFamily: "'Courier New', 'Special Elite', Courier, monospace",
        bg: "radial-gradient(ellipse at 50% 30%, #F5EDE0 0%, #E8DCB8 65%, #DACBA4 100%)",
        grid: "radial-gradient(rgba(140, 115, 80, 0.25) 1.5px, transparent 1.5px)",
        gridSize: "22px 22px",
        headerBg: "#FFFBF0",
        headerBorder: "2px dashed #B0A080",
        headerTextColor: "#3D3222",
        headerIcon: "📌",
        headerShadow: "2px 5px 12px rgba(0,0,0,0.12)",
        headerRadius: 8,
        cardBg: () => "#FFFDF5",
        cardBorder: "2px dashed #B8A888",
        cardShadow: "4px 8px 22px rgba(0,0,0,0.16)",
        cardRadius: 4,
        cardTitleColor: "#2D2418",
        cardTagBg: "#D9534F",
        cardTagColor: "#FFFFFF",
        cardBodyColor: "#3D3222",
        cardDivider: "2px dotted #B8A888",
        cardTapeBg: "rgba(217, 83, 79, 0.8)",
        leadActiveColor: "#1A1A1A",
        leadActiveBg: "rgba(255, 235, 59, 0.9)",
        leadActiveBorder: "1px solid #E6D020",
        leadActivePadding: "3px 10px",
        leadActiveRadius: 4,
        leadActiveShadow: "0 2px 8px rgba(0,0,0,0.14)",
        leadActiveScale: 1.25,
        leadPastColor: "#2B2520",
        leadFutureColor: "rgba(120, 105, 90, 0.38)",
        keyShadow: "4px 6px 14px rgba(0,0,0,0.18)",
        keyBorder: "2px dashed #FFFFFF",
        keyRadius: 8,
        eqColors: ["#D9534F", "#3D3222", "#E0A96D"],
        eqShadow: "0 2px 4px rgba(0,0,0,0.15)",
        eqRadius: 1,
        charStroke: "#2B2520",
        charStrokeWidth: 8,
        charHeadFill: "#FFFBF0",
        charHeadFilter: "drop-shadow(3px 4px 0px rgba(0,0,0,0.2))",
        charBlushColor: "rgba(217, 83, 79, 0.35)",
        charScarfFill: "#D9534F",
        charScarfStroke: "#2B2520",
        charMouthFill: "#D9534F",
      };

    case "pixel":
      return {
        id: "pixel",
        fontFamily: "'Press Start 2P', 'Courier New', Consolas, monospace",
        bg: "linear-gradient(180deg, #120D24 0%, #20133A 45%, #351B4F 100%)",
        grid: "repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.28) 0px, rgba(0, 0, 0, 0.28) 2px, transparent 2px, transparent 4px)",
        gridSize: "100% 4px",
        headerBg: "#0C102A",
        headerBorder: "3px solid #00F0FF",
        headerTextColor: "#FFE600",
        headerIcon: "👾",
        headerShadow: "0 0 16px rgba(0, 240, 255, 0.6)",
        headerRadius: 0,
        cardBg: () => "#0B1028",
        cardBorder: "4px solid #FFFFFF",
        cardShadow: "0 0 0 4px #000000, 8px 8px 0px #000000",
        cardRadius: 0,
        cardTitleColor: "#FFE600",
        cardTagBg: "#FF007F",
        cardTagColor: "#FFFFFF",
        cardBodyColor: "#E0E8FF",
        cardDivider: "2px solid #00F0FF",
        cardTapeBg: "#FF007F",
        leadActiveColor: "#00F0FF",
        leadActiveBg: undefined as string | undefined,
        leadActiveBorder: undefined as string | undefined,
        leadActivePadding: undefined as string | undefined,
        leadActiveRadius: undefined as number | string | undefined,
        leadActiveShadow: "0 0 18px #00F0FF, 0 0 35px #00F0FF",
        leadActiveScale: 1.28,
        leadPastColor: "#FFE600",
        leadFutureColor: "rgba(160, 140, 210, 0.38)",
        keyShadow: "0 0 20px #FF007F, 6px 6px 0px #000000",
        keyBorder: "3px solid #FFFFFF",
        keyRadius: 0,
        eqColors: ["#00F0FF", "#FFE600", "#FF007F"],
        eqShadow: "0 0 12px #00F0FF",
        eqRadius: 0,
        charStroke: "#FFFFFF",
        charStrokeWidth: 8,
        charHeadFill: "#0B1028",
        charHeadFilter: "drop-shadow(0 0 10px #00F0FF)",
        charBlushColor: "#FF007F",
        charScarfFill: "#FF007F",
        charScarfStroke: "#FFFFFF",
        charMouthFill: "#00F0FF",
      };

    case "brutalism":
      return {
        id: "brutalism",
        fontFamily: "'Arial Black', Impact, 'Trebuchet MS', sans-serif",
        bg: "#FAF7EE",
        grid: "radial-gradient(#000000 1.8px, transparent 1.8px)",
        gridSize: "28px 28px",
        headerBg: "#FFE600",
        headerBorder: "3px solid #000000",
        headerTextColor: "#000000",
        headerIcon: "⚡",
        headerShadow: "4px 4px 0px #000000",
        headerRadius: 0,
        cardBg: () => "#FFFFFF",
        cardBorder: "4px solid #000000",
        cardShadow: "8px 8px 0px #000000",
        cardRadius: 0,
        cardTitleColor: "#000000",
        cardTagBg: "#A6FF00",
        cardTagColor: "#000000",
        cardBodyColor: "#111111",
        cardDivider: "3px solid #000000",
        cardTapeBg: "#FFE600",
        leadActiveColor: "#A6FF00",
        leadActiveBg: "#000000",
        leadActiveBorder: "2px solid #000000",
        leadActivePadding: "3px 10px",
        leadActiveRadius: 0,
        leadActiveShadow: "3px 3px 0px #000000",
        leadActiveScale: 1.22,
        leadPastColor: "#000000",
        leadFutureColor: "rgba(0, 0, 0, 0.28)",
        keyShadow: "6px 6px 0px #000000",
        keyBorder: "4px solid #000000",
        keyRadius: 0,
        eqColors: ["#000000", "#FFE600", "#A6FF00"],
        eqShadow: "3px 3px 0px #000000",
        eqRadius: 0,
        charStroke: "#000000",
        charStrokeWidth: 10,
        charHeadFill: "#FFE600",
        charHeadFilter: "drop-shadow(4px 4px 0px #000000)",
        charBlushColor: "#A6FF00",
        charScarfFill: "#000000",
        charScarfStroke: "#000000",
        charMouthFill: "#000000",
      };

    case "whiteboard":
      return {
        id: "whiteboard",
        fontFamily: "'Segoe Print', 'Comic Sans MS', cursive, sans-serif",
        bg: "radial-gradient(ellipse at 50% 30%, #1E232B 0%, #14171E 65%, #0D0F13 100%)",
        grid: "linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px)",
        gridSize: "36px 36px",
        headerBg: "#222A36",
        headerBorder: "2px dashed #94A3B8",
        headerTextColor: "#FDE047",
        headerIcon: "💡",
        headerShadow: "0 6px 20px rgba(0,0,0,0.4)",
        headerRadius: 20,
        cardBg: () => "#1F2631",
        cardBorder: "2px dashed #94A3B8",
        cardShadow: "0 14px 35px rgba(0,0,0,0.5)",
        cardRadius: 12,
        cardTitleColor: "#FDE047",
        cardTagBg: "#38BDF8",
        cardTagColor: "#0F172A",
        cardBodyColor: "#E2E8F0",
        cardDivider: "1.5px dashed rgba(255, 255, 255, 0.2)",
        cardTapeBg: "rgba(56, 189, 248, 0.7)",
        leadActiveColor: "#FDE047",
        leadActiveBg: undefined as string | undefined,
        leadActiveBorder: undefined as string | undefined,
        leadActivePadding: undefined as string | undefined,
        leadActiveRadius: undefined as number | string | undefined,
        leadActiveShadow: "0 0 18px rgba(253, 224, 71, 0.85)",
        leadActiveScale: 1.35,
        leadPastColor: "#FFFFFF",
        leadFutureColor: "rgba(255, 255, 255, 0.3)",
        keyShadow: "0 10px 30px rgba(253, 224, 71, 0.3)",
        keyBorder: "2.5px dashed #FDE047",
        keyRadius: 28,
        eqColors: ["#FDE047", "#38BDF8", "#FFFFFF"],
        eqShadow: "0 0 10px rgba(253, 224, 71, 0.5)",
        eqRadius: 3,
        charStroke: "#E2E8F0",
        charStrokeWidth: 7,
        charHeadFill: "#1F2631",
        charHeadFilter: "drop-shadow(0 0 10px rgba(255,255,255,0.4))",
        charBlushColor: "rgba(253, 224, 71, 0.4)",
        charScarfFill: "#38BDF8",
        charScarfStroke: "#E2E8F0",
        charMouthFill: "#FDE047",
      };

    default: // "cozy"
      return {
        id: "cozy",
        fontFamily: "'Plus Jakarta Sans', 'Segoe UI', Roboto, sans-serif",
        bg: "radial-gradient(ellipse at 50% 28%, #FFFDF9 0%, #F5EFE1 65%, #ECE2CE 100%)",
        grid: "linear-gradient(to right, rgba(200, 190, 175, 0.22) 1px, transparent 1px), linear-gradient(to bottom, rgba(200, 190, 175, 0.22) 1px, transparent 1px)",
        gridSize: "42px 42px",
        headerBg: "#FFFFFF",
        headerBorder: "2px solid #E5DCC5",
        headerTextColor: "#3D405B",
        headerIcon: "🌿",
        headerShadow: "0 6px 22px rgba(0,0,0,0.06)",
        headerRadius: 30,
        cardBg: (col: string) => col || "#FFF3B0",
        cardBorder: "1px solid rgba(0,0,0,0.06)",
        cardShadow: "0 14px 35px rgba(0,0,0,0.12), 0 4px 10px rgba(0,0,0,0.06)",
        cardRadius: 12,
        cardTitleColor: "#2B2D42",
        cardTagBg: "rgba(255,255,255,0.75)",
        cardTagColor: "#E07A5F",
        cardBodyColor: "#3D405B",
        cardDivider: "1.5px dashed rgba(61, 64, 91, 0.2)",
        cardTapeBg: "rgba(224, 122, 95, 0.8)",
        leadActiveColor: "#E07A5F",
        leadActiveBg: undefined as string | undefined,
        leadActiveBorder: undefined as string | undefined,
        leadActivePadding: undefined as string | undefined,
        leadActiveRadius: undefined as number | string | undefined,
        leadActiveShadow: "0 4px 18px rgba(224, 122, 95, 0.4)",
        leadActiveScale: 1.35,
        leadPastColor: "#1D1E2C",
        leadFutureColor: "rgba(61, 64, 91, 0.35)",
        keyShadow: "0 16px 40px rgba(224, 122, 95, 0.4)",
        keyBorder: "3px solid rgba(255,255,255,0.4)",
        keyRadius: 36,
        eqColors: ["#E07A5F", "#F4A261"],
        eqShadow: "0 0 10px rgba(224, 122, 95, 0.4)",
        eqRadius: 3,
        charStroke: "#2B2D42",
        charStrokeWidth: 7,
        charHeadFill: "#FFFFFF",
        charHeadFilter: "url(#cozy-shadow)",
        charBlushColor: "rgba(224, 122, 95, 0.35)",
        charScarfFill: "#E07A5F",
        charScarfStroke: "#2B2D42",
        charMouthFill: "#E07A5F",
      };
  }
}

export const CozyStorytellingVideo: React.FC<CozyStorytellingProps> = ({
  scenes: propScenes,
  audioSrc = "audio_cozy.mp3",
  totalDurationInFrames,
  channelTag = "☕ 60 Ngày Kỷ Luật • Thay Đổi Bản Thân",
  style = "cozy",
  character = "stickman",
  timedDialogue = false,
}) => {
  const currentFrame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();

  const theme = getTheme(style);

  const isHorizontal = width > height;
  const isSquare = Math.abs(width - height) < 150;
  const isTall = height >= width * 1.3;

  // Adaptive layout positions
  const headerTop = isHorizontal ? 26 : isSquare ? 35 : 85;
  const headerFontSize = isHorizontal || isSquare ? 18 : 22;

  let charTop = height * 0.09;
  const charLeft: string | number = "50%";
  let charScale = isTall ? (width < 1100 ? 1.05 : 1.15) : 0.95;

  if (isHorizontal) {
    charTop = height * 0.10;
    charScale = 0.92;
  } else if (isSquare) {
    charTop = height * 0.08;
    charScale = 0.82;
  } else if (!isTall) {
    charTop = height * 0.08;
    charScale = 1.0;
  }

  const typoTop = isHorizontal ? height * 0.58 : isSquare ? height * 0.58 : height * 0.52;
  const typoBottom = isTall ? 95 : 55;
  const typoLeft = isHorizontal ? 60 : 40;
  const typoRight = isHorizontal ? 60 : 40;
  const leadFontSize = isTall ? 48 : isHorizontal ? 40 : 34;
  const keyFontSize = isTall ? 52 : isHorizontal ? 44 : 38;
  const keyIconSize = isTall ? 44 : 36;
  const numLights = isHorizontal ? 9 : 6;

  const activeScenesList = propScenes && propScenes.length > 0 ? propScenes : SCENES;
  const totalFrames =
    totalDurationInFrames ||
    activeScenesList[activeScenesList.length - 1]?.endFrame ||
    448;

  // Find active scene and its index in the story
  const timedScene = activeScenesList.find(
    (s) => currentFrame >= s.startFrame && currentFrame < s.endFrame
  );
  const activeScene =
    activeScenesList.find(
      (s) => currentFrame >= s.startFrame && currentFrame < s.endFrame
    ) || (timedDialogue
      ? [...activeScenesList].reverse().find(s => currentFrame >= s.startFrame) || activeScenesList[0]
      : activeScenesList[activeScenesList.length - 1]);

  const sceneIndex = Math.max(0, activeScenesList.indexOf(activeScene));
  const sceneVisible = !timedDialogue || Boolean(timedScene);
  const speakingNow = sceneVisible && activeScene.leadWords.some(w => currentFrame >= w.start && currentFrame < w.end);
  const actionFrame = currentFrame - (activeScene.actionStart ?? activeScene.startFrame);
  const action = timedDialogue && sceneVisible && actionFrame >= 0 ? activeScene.action : 'idle';
  const actionTime = Math.max(0, actionFrame);
  const actionStrength = Math.min(1, actionTime / 8);
  const actionX = action === 'walk' ? Math.sin(actionTime * 0.08) * 65 * actionStrength : 0;
  const actionY = action === 'celebrate' ? -Math.abs(Math.sin(actionTime * 0.18)) * 22 * actionStrength
    : action === 'walk' ? -Math.abs(Math.sin(actionTime * 0.25)) * 8 * actionStrength
    : action === 'nod' ? Math.sin(actionTime * 0.25) * 6 * actionStrength : 0;
  const actionRotation = action === 'shake_head' ? Math.sin(actionTime * 0.22) * 6 * actionStrength
    : action === 'think' ? -6 * actionStrength : 0;

  // Dynamic Card Positions: Organically orbiting around the subject
  const noteWidth = isTall
    ? Math.min(340, width * 0.34)
    : isSquare
    ? 320
    : Math.min(380, width * 0.30);

  // 1. Vertical mode positions (Tall: 9:16, 10:16, 4:5)
  const verticalPositions = [
    { top: height * 0.35, right: Math.max(26, width * 0.05), left: undefined as string | number | undefined, rot: 2.8, origin: "top right", isCenter: false },
    { top: height * 0.35, left: Math.max(26, width * 0.05), right: undefined as string | number | undefined, rot: -2.8, origin: "top left", isCenter: false },
    { top: height * 0.18, right: Math.max(26, width * 0.04), left: undefined as string | number | undefined, rot: -2.0, origin: "bottom right", isCenter: false },
    { top: height * 0.18, left: Math.max(26, width * 0.04), right: undefined as string | number | undefined, rot: 2.2, origin: "bottom left", isCenter: false },
    { top: height * 0.36, left: "50%", right: undefined as string | number | undefined, rot: -0.6, origin: "center top", isCenter: true },
  ];

  // 2. Landscape mode positions (16:9, 16:10, 4:3)
  const horizontalPositions = [
    { top: height * 0.14, left: width * 0.65, right: undefined as string | number | undefined, rot: 2.5, origin: "top left", isCenter: false },
    { top: height * 0.14, right: width * 0.65, left: undefined as string | number | undefined, rot: -2.5, origin: "top right", isCenter: false },
    { top: height * 0.30, left: width * 0.64, right: undefined as string | number | undefined, rot: -2.2, origin: "top left", isCenter: false },
    { top: height * 0.30, right: width * 0.64, left: undefined as string | number | undefined, rot: 2.2, origin: "top right", isCenter: false },
  ];

  // 3. Square mode positions (1:1)
  const squarePositions = [
    { top: height * 0.12, right: 32, left: undefined as string | number | undefined, rot: 2.2, origin: "top right", isCenter: false },
    { top: height * 0.12, left: 32, right: undefined as string | number | undefined, rot: -2.2, origin: "top left", isCenter: false },
    { top: height * 0.34, right: 32, left: undefined as string | number | undefined, rot: -2.5, origin: "top right", isCenter: false },
    { top: height * 0.34, left: 32, right: undefined as string | number | undefined, rot: 2.5, origin: "top left", isCenter: false },
    { top: height * 0.37, left: "50%", right: undefined as string | number | undefined, rot: -0.6, origin: "center top", isCenter: true },
  ];

  const posConfig = isHorizontal
    ? horizontalPositions[sceneIndex % horizontalPositions.length]
    : isSquare
    ? squarePositions[sceneIndex % squarePositions.length]
    : verticalPositions[sceneIndex % verticalPositions.length];

  // Note Spring entrance per scene
  const noteSpring = spring({
    frame: Math.max(0, currentFrame - activeScene.startFrame),
    fps,
    config: { damping: 14, stiffness: 160 },
  });

  // Key Phrase Spring Entrance
  const keyDelay = Math.max(0, currentFrame - activeScene.keyPhrase.start);
  const keySpring = spring({
    frame: keyDelay,
    fps,
    config: { damping: 11, stiffness: 200 },
  });
  const isKeyActive = sceneVisible && currentFrame >= activeScene.keyPhrase.start && currentFrame < activeScene.keyPhrase.end;

  // Character organic motions
  const breathe = Math.sin(currentFrame * 0.12) * 5;
  const isBlinking = currentFrame % 75 >= 70;
  const talkMouth = timedDialogue && !speakingNow ? 0 : Math.abs(Math.sin(currentFrame * 0.75)) * 14;
  const steamOffset = (currentFrame * 1.5) % 60;

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: theme.fontFamily,
      }}
    >
      {/* Audio Track */}
      {audioSrc && <Audio src={staticFile(audioSrc)} />}

      {/* AMBIENT BACKGROUND */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: theme.bg,
        }}
      />

      {/* Grid Overlay */}
      {theme.grid && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: theme.grid,
            backgroundSize: theme.gridSize || "42px 42px",
            pointerEvents: "none",
          }}
        />
      )}

      {/* THEME SPECIFIC DECOR */}
      {theme.id === "cozy" && (
        <div
          style={{
            position: "absolute",
            top: 25,
            left: 60,
            right: 60,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            zIndex: 5,
          }}
        >
          {[0, 1, 2, 3, 4, 5, 6, 7, 8].slice(0, numLights).map((lightIdx) => {
            const bulbGlow = Math.sin(currentFrame * 0.1 + lightIdx * 1.3) * 0.3 + 0.7;
            return (
              <div key={lightIdx} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ width: 2, height: 25 + (lightIdx % 3) * 16, backgroundColor: "#b7b7a4" }} />
                <div
                  style={{
                    width: 18,
                    height: 24,
                    borderRadius: "50% 50% 45% 45%",
                    backgroundColor: "#FFE5A3",
                    opacity: bulbGlow,
                    boxShadow: `0 4px 20px rgba(255, 215, 0, ${bulbGlow * 0.85})`,
                    border: "1.5px solid #ffcc00",
                  }}
                />
              </div>
            );
          })}
        </div>
      )}

      {theme.id === "midnight" && (
        <>
          {/* Crescent Moon */}
          <div
            style={{
              position: "absolute",
              top: 40,
              right: isHorizontal ? 80 : 50,
              fontSize: isHorizontal ? 48 : 56,
              filter: "drop-shadow(0 0 25px rgba(244, 226, 187, 0.8))",
              opacity: 0.9,
              zIndex: 5,
            }}
          >
            🌙
          </div>
          {/* Glowing Bokeh Orbs */}
          {[
            { x: 0.15, y: 0.2, size: 140, color: "rgba(244, 226, 187, 0.12)" },
            { x: 0.85, y: 0.28, size: 180, color: "rgba(56, 189, 248, 0.10)" },
            { x: 0.2, y: 0.75, size: 160, color: "rgba(244, 162, 97, 0.10)" },
            { x: 0.8, y: 0.78, size: 200, color: "rgba(244, 226, 187, 0.12)" },
          ].map((b, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                top: b.y * height,
                left: b.x * width,
                width: b.size,
                height: b.size,
                borderRadius: "50%",
                background: b.color,
                filter: "blur(40px)",
                transform: `scale(${1 + Math.sin(currentFrame * 0.05 + i) * 0.2})`,
                pointerEvents: "none",
                zIndex: 3,
              }}
            />
          ))}
        </>
      )}

      {theme.id === "pixel" && (
        <>
          {/* 8-Bit Pixel Clouds */}
          <div
            style={{
              position: "absolute",
              top: 50,
              left: `${(currentFrame * 1.2) % (width + 200) - 100}px`,
              fontSize: 36,
              opacity: 0.75,
              zIndex: 4,
            }}
          >
            ☁️
          </div>
          <div
            style={{
              position: "absolute",
              top: 110,
              right: 60,
              fontSize: 28,
              opacity: 0.85,
              zIndex: 4,
            }}
          >
            👾
          </div>
        </>
      )}

      {theme.id === "brutalism" && (
        <>
          {/* Neo-brutalist Floating Stickers */}
          <div
            style={{
              position: "absolute",
              top: 40,
              right: 40,
              background: "#A6FF00",
              color: "#000000",
              border: "3px solid #000000",
              padding: "6px 14px",
              fontWeight: 900,
              fontSize: 14,
              boxShadow: "4px 4px 0px #000000",
              transform: "rotate(6deg)",
              zIndex: 6,
            }}
          >
            ⚡ 100% FOCUS
          </div>
        </>
      )}

      {/* TOP HEADER BADGE */}
      <div
        style={{
          position: "absolute",
          top: headerTop,
          maxWidth: width * 0.88,
          boxSizing: 'border-box',
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: isHorizontal || isSquare ? "8px 24px" : "12px 32px",
          borderRadius: theme.headerRadius,
          backgroundColor: theme.headerBg,
          border: theme.headerBorder,
          boxShadow: theme.headerShadow,
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: headerFontSize }}>{theme.headerIcon}</span>
        <span
          style={{
            fontSize: headerFontSize,
            fontWeight: 800,
            color: theme.headerTextColor,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {activeScene.badge}
        </span>
      </div>

      {/* FLOATING SPARKLES / PARTICLES */}
      {[
        { xRatio: 0.12, yRatio: 0.25, s: 0.8, d: 20 },
        { xRatio: 0.88, yRatio: 0.32, s: 1.2, d: 45 },
        { xRatio: 0.15, yRatio: 0.72, s: 0.9, d: 70 },
        { xRatio: 0.85, yRatio: 0.78, s: 1.1, d: 90 },
      ].map((p, i) => {
        const floatY = Math.sin(currentFrame * 0.08 + p.d) * 18;
        const icon = theme.id === "midnight" ? "✦" : theme.id === "pixel" ? "◆" : theme.id === "brutalism" ? "■" : "✨";
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: p.yRatio * height + floatY,
              left: p.xRatio * width,
              fontSize: 24 * p.s,
              opacity: theme.id === "midnight" ? 0.75 : 0.55,
              color: theme.headerTextColor,
              pointerEvents: "none",
            }}
          >
            {icon}
          </div>
        );
      })}

      {/* CENTER STAGE: 2D ANIMATED STORYTELLER CHARACTER */}
      <div
        style={{
          position: "absolute",
          top: charTop,
          left: charLeft,
          transform: `translateX(-50%) translateY(${breathe}px) scale(${charScale})`,
          width: 800,
          height: 600,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 8,
        }}
      >
        <svg width="800" height="600" viewBox="0 0 800 600">
          <defs>
            <filter id="cozy-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="6" stdDeviation="6" floodOpacity="0.12" />
            </filter>
          </defs>

          {/* Rug / Stand base */}
          <ellipse cx="400" cy="510" rx="230" ry="28" fill={theme.id === "midnight" ? "#182032" : "#EADBC8"} opacity="0.6" />
          <ellipse cx="400" cy="505" rx="170" ry="18" fill="rgba(0,0,0,0.08)" />

          {/* Cushion / Seat */}
          <ellipse
            cx="400"
            cy="460"
            rx="72"
            ry="20"
            fill={theme.charScarfFill}
            stroke={theme.charStroke}
            strokeWidth={theme.id === "brutalism" ? 4 : 2}
          />
          <rect
            x="328"
            y="460"
            width="144"
            height="15"
            rx={theme.id === "brutalism" || theme.id === "pixel" ? 0 : 4}
            fill={theme.charScarfFill}
            stroke={theme.charStroke}
            strokeWidth={theme.id === "brutalism" ? 3 : 1}
          />

          {/* Coffee Mug on small wooden stand */}
          <g transform="translate(560, 430)">
            <ellipse cx="25" cy="55" rx="35" ry="10" fill="#D4A373" />
            <rect x="22" y="55" width="6" height="35" fill="#BC6C25" />
            <rect
              x="12"
              y="20"
              width="26"
              height="30"
              rx={theme.id === "pixel" || theme.id === "brutalism" ? 0 : 5}
              fill={theme.charHeadFill}
              stroke={theme.charStroke}
              strokeWidth={theme.charStrokeWidth > 7 ? 4 : 3}
            />
            <path d="M 38 26 Q 48 35 38 44" fill="none" stroke={theme.charStroke} strokeWidth="3" />
            <ellipse cx="25" cy="22" rx="11" ry="4" fill="#6F4E37" />
            {/* Steaming vapor */}
            <path
              d={`M 22 ${15 - steamOffset * 0.4} Q 18 ${8 - steamOffset * 0.4} 25 ${0 - steamOffset * 0.4}`}
              fill="none"
              stroke={theme.id === "midnight" ? "rgba(244, 226, 187, 0.7)" : "rgba(180, 160, 140, 0.7)"}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d={`M 28 ${18 - steamOffset * 0.5} Q 34 ${10 - steamOffset * 0.5} 27 ${2 - steamOffset * 0.5}`}
              fill="none"
              stroke={theme.id === "midnight" ? "rgba(244, 226, 187, 0.6)" : "rgba(180, 160, 140, 0.6)"}
              strokeWidth="2"
              strokeLinecap="round"
            />
          </g>

          {/* Plant / Mascot companion */}
          <g transform="translate(180, 420)">
            <polygon
              points="15,40 45,40 40,80 20,80"
              fill={theme.id === "midnight" ? "#1E293B" : "#DDA15E"}
              stroke={theme.charStroke}
              strokeWidth="2"
            />
            <path d="M 30 40 Q 10 15 5 25 Q 20 40 30 40" fill="#81B29A" stroke={theme.charStroke} strokeWidth="2" />
            <path d="M 30 40 Q 50 10 55 20 Q 40 40 30 40" fill="#81B29A" stroke={theme.charStroke} strokeWidth="2" />
            <path d="M 30 40 Q 30 -5 32 10 Q 32 35 30 40" fill="#606C38" stroke={theme.charStroke} strokeWidth="2" />
          </g>

          {/* DYNAMIC CHARACTER RENDERING ACCORDING TO CHARACTER PROP */}
          <g transform={`translate(${actionX}, ${actionY}) rotate(${actionRotation}, 400, 350)`}>
          {(() => {
            const charType = character || "stickman";

            if (charType === "cat") {
              // =================== 2. CAT (MÈO BÉO CHILL) ===================
              const tailWag = Math.sin(currentFrame * 0.14) * 14;
              return (
                <g id="character-cat">
                  {/* Fluffy Tail swaying */}
                  <path
                    d={`M 335 450 Q ${290 + tailWag} 430 ${285 + tailWag * 1.4} 365 Q ${305 + tailWag * 1.4} 355 ${315 + tailWag} 415 Q ${325 + tailWag * 0.5} 450 350 460 Z`}
                    fill={theme.charHeadFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth - 1}
                    strokeLinejoin="round"
                  />

                  {/* Hind Paws (folded sitting on cushion) */}
                  <ellipse cx="342" cy="465" rx="22" ry="13" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />
                  <line x1="335" y1="462" x2="335" y2="472" stroke={theme.charStroke} strokeWidth="2" strokeLinecap="round" />
                  <line x1="344" y1="462" x2="344" y2="473" stroke={theme.charStroke} strokeWidth="2" strokeLinecap="round" />

                  <ellipse cx="458" cy="465" rx="22" ry="13" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />
                  <line x1="456" y1="462" x2="456" y2="473" stroke={theme.charStroke} strokeWidth="2" strokeLinecap="round" />
                  <line x1="465" y1="462" x2="465" y2="472" stroke={theme.charStroke} strokeWidth="2" strokeLinecap="round" />

                  {/* Chubby Cat Body */}
                  <ellipse
                    cx="400"
                    cy="405"
                    rx="68"
                    ry="60"
                    fill={theme.charHeadFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth}
                  />

                  {/* Softer Creamy Belly Patch */}
                  <ellipse
                    cx="400"
                    cy="415"
                    rx="44"
                    ry="40"
                    fill={theme.id === "midnight" ? "#1E293B" : "#FFF9EE"}
                    opacity="0.95"
                  />

                  {/* Cozy Scarf & Bell */}
                  <ellipse cx="400" cy="336" rx="48" ry="16" fill={theme.charScarfFill} stroke={theme.charScarfStroke} strokeWidth="3.5" />
                  <path d="M 412 342 L 426 395 L 444 390 L 428 342 Z" fill={theme.charScarfFill} stroke={theme.charScarfStroke} strokeWidth="3" />
                  <line x1="426" y1="395" x2="424" y2="407" stroke={theme.charScarfFill} strokeWidth="2.5" />
                  <line x1="435" y1="393" x2="435" y2="407" stroke={theme.charScarfFill} strokeWidth="2.5" />
                  <circle cx="400" cy="344" r="8" fill="#F4A261" stroke={theme.charStroke} strokeWidth="2.5" />
                  <circle cx="400" cy="346" r="2.5" fill={theme.charStroke} />

                  {/* Front Paws / Arms */}
                  {activeScene.characterState === "reflecting" ? (
                    <>
                      <path d="M 360 360 Q 345 385 365 395" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <ellipse cx="365" cy="395" rx="14" ry="11" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                      <path d="M 435 360 Q 455 345 440 325" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <circle cx="438" cy="322" r="12" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                    </>
                  ) : activeScene.characterState === "loyal" ? (
                    <>
                      <path d="M 360 360 Q 365 390 376 400" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <ellipse cx="376" cy="400" rx="14" ry="11" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                      <path d="M 440 360 Q 435 390 424 400" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <ellipse cx="424" cy="400" rx="14" ry="11" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                      <circle cx="400" cy="398" r="9" fill="#E63946" stroke="#FFFFFF" strokeWidth="2" />
                    </>
                  ) : (
                    <>
                      <path d="M 360 360 Q 350 395 368 405" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <ellipse cx="368" cy="405" rx="14" ry="11" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                      <path d="M 440 360 Q 450 395 432 405" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} strokeLinecap="round" />
                      <ellipse cx="432" cy="405" rx="14" ry="11" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                    </>
                  )}

                  {/* Cat Head */}
                  <ellipse
                    cx="400"
                    cy="265"
                    rx="62"
                    ry="54"
                    fill={theme.charHeadFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth}
                    filter={theme.charHeadFilter}
                  />

                  {/* Ears with Pink Inner */}
                  <polygon points="345,248 330,192 376,218" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinejoin="round" />
                  <polygon points="348,238 338,202 370,220" fill={theme.charBlushColor} />

                  <polygon points="455,248 470,192 424,218" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinejoin="round" />
                  <polygon points="452,238 462,202 430,220" fill={theme.charBlushColor} />

                  {/* Whiskers (3 on each cheek) */}
                  <line x1="326" y1="264" x2="362" y2="267" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />
                  <line x1="322" y1="274" x2="362" y2="273" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />
                  <line x1="328" y1="284" x2="364" y2="279" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />

                  <line x1="474" y1="264" x2="438" y2="267" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />
                  <line x1="478" y1="274" x2="438" y2="273" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />
                  <line x1="472" y1="284" x2="436" y2="279" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />

                  {/* Cat Eyes */}
                  {!isBlinking ? (
                    <>
                      <ellipse cx="383" cy="254" rx="7" ry="8" fill={theme.charStroke} />
                      <circle cx="381" cy="251" r="2.5" fill="#FFFFFF" />
                      <ellipse cx="417" cy="254" rx="7" ry="8" fill={theme.charStroke} />
                      <circle cx="415" cy="251" r="2.5" fill="#FFFFFF" />
                    </>
                  ) : (
                    <>
                      <path d="M 374 256 Q 384 250 392 256" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                      <path d="M 408 256 Q 416 250 426 256" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                    </>
                  )}

                  {/* Blushing Cheeks */}
                  <circle cx="365" cy="272" r="9" fill={theme.charBlushColor} />
                  <circle cx="435" cy="272" r="9" fill={theme.charBlushColor} />

                  {/* Cat Tiny Nose */}
                  <polygon points="396,266 404,266 400,271" fill={theme.charBlushColor} stroke={theme.charStroke} strokeWidth="1.5" />

                  {/* Cat Mouth (:3) */}
                  {activeScene.characterState === "sad" ? (
                    <path d="M 392 278 Q 400 272 408 278" fill="none" stroke={theme.charStroke} strokeWidth="3" strokeLinecap="round" />
                  ) : (
                    <>
                      <path d="M 392 273 Q 396 278 400 273 Q 404 278 408 273" fill="none" stroke={theme.charStroke} strokeWidth="3" strokeLinecap="round" />
                      <ellipse cx="400" cy="278" rx="5" ry={Math.max(2, talkMouth * 0.35)} fill={theme.charMouthFill} stroke={theme.charStroke} strokeWidth="2" />
                    </>
                  )}
                </g>
              );
            } else if (charType === "hoodie") {
              // =================== 3. HOODIE (CẬU BÉ LOFI HOODIE) ===================
              return (
                <g id="character-hoodie">
                  {/* Sitting Legs & Sneakers */}
                  <path d="M 375 440 L 350 478 L 332 502" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M 425 440 L 450 478 L 468 502" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" strokeLinejoin="round" />
                  <rect x="316" y="498" width="32" height="14" rx="6" fill="#FFFFFF" stroke={theme.charStroke} strokeWidth="2.5" />
                  <line x1="324" y1="504" x2="336" y2="504" stroke="#E63946" strokeWidth="2.5" />
                  <rect x="452" y="498" width="32" height="14" rx="6" fill="#FFFFFF" stroke={theme.charStroke} strokeWidth="2.5" />
                  <line x1="460" y1="504" x2="472" y2="504" stroke="#E63946" strokeWidth="2.5" />

                  {/* Oversized Comfy Hoodie Sweater */}
                  <ellipse cx="400" cy="320" rx="55" ry="16" fill={theme.charScarfFill} stroke={theme.charStroke} strokeWidth="3" />
                  <path
                    d="M 345 310 C 320 370 324 430 336 450 L 464 450 C 476 430 480 370 455 310 Z"
                    fill={theme.charScarfFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth}
                    strokeLinejoin="round"
                  />

                  {/* Front Kangaroo Pocket */}
                  <path d="M 360 405 L 440 405 L 448 442 L 352 442 Z" fill="rgba(0,0,0,0.14)" stroke={theme.charStroke} strokeWidth="2.5" />

                  {/* Hoodie Drawstrings */}
                  <path d="M 386 335 Q 384 365 385 382" fill="none" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" />
                  <circle cx="385" cy="384" r="3" fill="#FFFFFF" />
                  <path d="M 414 335 Q 416 365 415 382" fill="none" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" />
                  <circle cx="415" cy="384" r="3" fill="#FFFFFF" />

                  {/* Arms based on scene state */}
                  {activeScene.characterState === "reflecting" ? (
                    <>
                      <line x1="345" y1="355" x2="335" y2="410" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                      <path d="M 455 355 Q 485 340 472 270" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                      <circle cx="468" cy="265" r="9" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                    </>
                  ) : (
                    <>
                      <path d="M 345 355 Q 330 400 365 425" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                      <path d="M 455 355 Q 470 400 435 425" fill="none" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                    </>
                  )}

                  {/* Big Cozy Hood Outer */}
                  <ellipse cx="400" cy="254" rx="66" ry="66" fill={theme.charScarfFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} />

                  {/* Face Opening */}
                  <ellipse cx="400" cy="258" rx="46" ry="46" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />

                  {/* Hair Bangs */}
                  <path d="M 362 232 Q 382 250 400 236 Q 416 250 438 232" fill={theme.id === "midnight" ? "#0F172A" : "#2B2D42"} stroke={theme.charStroke} strokeWidth="2.5" />

                  {/* Chunky Lofi Headphones over Hood */}
                  <path d="M 338 252 A 66 66 0 0 1 462 252" fill="none" stroke={theme.charStroke} strokeWidth="7" strokeLinecap="round" />
                  <path d="M 365 196 A 58 58 0 0 1 435 196" fill="none" stroke={theme.id === "midnight" ? "#F4E2BB" : "#F4A261"} strokeWidth="5" strokeLinecap="round" />
                  <rect x="325" y="235" width="16" height="38" rx="8" fill={theme.id === "midnight" ? "#F4E2BB" : "#F4A261"} stroke={theme.charStroke} strokeWidth="3" />
                  <rect x="459" y="235" width="16" height="38" rx="8" fill={theme.id === "midnight" ? "#F4E2BB" : "#F4A261"} stroke={theme.charStroke} strokeWidth="3" />

                  {/* Eyes */}
                  {!isBlinking ? (
                    <>
                      <circle cx="382" cy="256" r="5.5" fill={theme.charStroke} />
                      <circle cx="380" cy="254" r="2" fill="#FFFFFF" />
                      <circle cx="418" cy="256" r="5.5" fill={theme.charStroke} />
                      <circle cx="416" cy="254" r="2" fill="#FFFFFF" />
                    </>
                  ) : (
                    <>
                      <path d="M 374 256 Q 382 250 390 256" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                      <path d="M 410 256 Q 418 250 426 256" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                    </>
                  )}

                  {/* Blushing Cheeks */}
                  <circle cx="372" cy="268" r="8" fill={theme.charBlushColor} />
                  <circle cx="428" cy="268" r="8" fill={theme.charBlushColor} />

                  {/* Mouth */}
                  {activeScene.characterState === "sad" ? (
                    <path d="M 390 282 Q 400 274 410 282" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                  ) : (
                    <ellipse cx="400" cy="278" rx="7" ry={Math.max(3, talkMouth * 0.4)} fill={theme.charMouthFill} stroke={theme.charStroke} strokeWidth="2.5" />
                  )}
                </g>
              );
            } else if (charType === "bear") {
              // =================== 4. BEAR (GẤU TEDDY THƯ THÁI) ===================
              const bearMainColor = theme.id === "midnight" ? "#2B374E" : "#B07D53";
              const bearLightColor = theme.id === "midnight" ? "#F4E2BB" : "#D4A373";
              return (
                <g id="character-bear">
                  {/* Round Teddy Ears */}
                  <circle cx="342" cy="206" r="22" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} />
                  <circle cx="342" cy="206" r="12" fill={bearLightColor} />
                  <circle cx="458" cy="206" r="22" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} />
                  <circle cx="458" cy="206" r="12" fill={bearLightColor} />

                  {/* Chubby Teddy Body */}
                  <ellipse cx="400" cy="412" rx="74" ry="64" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} />

                  {/* Belly Oval Patch */}
                  <ellipse cx="400" cy="422" rx="46" ry="44" fill={bearLightColor} stroke={theme.charStroke} strokeWidth="2" />
                  <line x1="400" y1="392" x2="400" y2="456" stroke="rgba(0,0,0,0.22)" strokeWidth="2" strokeDasharray="4 3" />

                  {/* Round Feet with Paw Pads */}
                  <ellipse cx="334" cy="466" rx="24" ry="16" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />
                  <ellipse cx="334" cy="466" rx="14" ry="9" fill={bearLightColor} />

                  <ellipse cx="466" cy="466" rx="24" ry="16" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />
                  <ellipse cx="466" cy="466" rx="14" ry="9" fill={bearLightColor} />

                  {/* Arms */}
                  <ellipse cx="336" cy="385" rx="18" ry="32" transform="rotate(22 336 385)" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />
                  <ellipse cx="464" cy="385" rx="18" ry="32" transform="rotate(-22 464 385)" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth - 2} />

                  {/* Neck Scarf */}
                  <ellipse cx="400" cy="330" rx="46" ry="14" fill={theme.charScarfFill} stroke={theme.charScarfStroke} strokeWidth="3" />
                  <path d="M 408 335 L 420 385 L 436 380 L 424 335 Z" fill={theme.charScarfFill} stroke={theme.charScarfStroke} strokeWidth="3" />

                  {/* Head */}
                  <circle cx="400" cy="260" r="56" fill={bearMainColor} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} filter={theme.charHeadFilter} />

                  {/* Teddy Muzzle */}
                  <ellipse cx="400" cy="276" rx="28" ry="20" fill={bearLightColor} stroke={theme.charStroke} strokeWidth="2" />
                  <polygon points="393,268 407,268 400,276" fill={theme.charStroke} />
                  <path d="M 400 276 L 400 283 M 394 283 Q 400 288 406 283" fill="none" stroke={theme.charStroke} strokeWidth="2.5" strokeLinecap="round" />
                  <ellipse cx="400" cy="284" rx="5" ry={Math.max(2, talkMouth * 0.35)} fill={theme.charMouthFill} stroke={theme.charStroke} strokeWidth="2" />

                  {/* Button Eyes */}
                  {!isBlinking ? (
                    <>
                      <circle cx="378" cy="250" r="6" fill={theme.charStroke} />
                      <circle cx="376" cy="248" r="2" fill="#FFFFFF" />
                      <circle cx="422" cy="250" r="6" fill={theme.charStroke} />
                      <circle cx="420" cy="248" r="2" fill="#FFFFFF" />
                    </>
                  ) : (
                    <>
                      <line x1="372" y1="250" x2="384" y2="250" stroke={theme.charStroke} strokeWidth="3" strokeLinecap="round" />
                      <line x1="416" y1="250" x2="428" y2="250" stroke={theme.charStroke} strokeWidth="3" strokeLinecap="round" />
                    </>
                  )}

                  {/* Blushing */}
                  <circle cx="362" cy="268" r="8" fill={theme.charBlushColor} />
                  <circle cx="438" cy="268" r="8" fill={theme.charBlushColor} />
                </g>
              );
            } else if (charType === "bot") {
              // =================== 5. BOT (ROBOT AI TÍ HON) ===================
              const botGlow = Math.sin(currentFrame * 0.25) * 0.3 + 0.7;
              return (
                <g id="character-bot">
                  {/* Antenna with Pulsing Glow */}
                  <line x1="400" y1="190" x2="400" y2="155" stroke={theme.charStroke} strokeWidth="4" strokeLinecap="round" />
                  <circle cx="400" cy="150" r="11" fill="#38BDF8" opacity={botGlow} stroke={theme.charStroke} strokeWidth="2.5" filter="drop-shadow(0 0 10px #38BDF8)" />

                  {/* Hover Thruster Flame */}
                  <ellipse cx="400" cy="460" rx="38" ry="12" fill={theme.charStroke} />
                  <polygon points="375,465 425,465 400,495" fill="#38BDF8" opacity="0.85" filter="drop-shadow(0 0 10px #38BDF8)" />
                  <polygon points="385,465 415,465 400,485" fill="#FFFFFF" opacity="0.95" />

                  {/* Robot Neck Connection Joint */}
                  <rect x="385" y="310" width="30" height="35" rx="4" fill={theme.charStroke} />
                  <ellipse cx="400" cy="328" rx="8" ry="4" fill="#38BDF8" opacity={botGlow} />

                  {/* Robot Chassis Body */}
                  <rect x="345" y="340" width="110" height="105" rx="24" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} />

                  {/* Chest Panel & LED Meters */}
                  <rect x="365" y="365" width="70" height="24" rx="6" fill={theme.id === "midnight" ? "#0F172A" : "#1E293B"} stroke={theme.charStroke} strokeWidth="2" />
                  <rect x="372" y="371" width="14" height="12" rx="2" fill="#22C55E" />
                  <rect x="393" y="371" width="14" height="12" rx="2" fill="#22C55E" />
                  <rect x="414" y="371" width="14" height="12" rx="2" fill="#38BDF8" />
                  <circle cx="400" cy="415" r="10" fill="#38BDF8" stroke={theme.charStroke} strokeWidth="2" opacity={botGlow} />

                  {/* Arms & Grippers */}
                  <path d="M 345 365 Q 315 390 325 420" fill="none" stroke={theme.charStroke} strokeWidth="6" strokeLinecap="round" />
                  <path d="M 320 415 Q 308 425 320 435" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />

                  <path d="M 455 365 Q 485 390 475 420" fill="none" stroke={theme.charStroke} strokeWidth="6" strokeLinecap="round" />
                  <path d="M 480 415 Q 492 425 480 435" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />

                  {/* Robot Monitor Head Outer */}
                  <rect x="330" y="195" width="140" height="120" rx="30" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} filter={theme.charHeadFilter} />

                  {/* Visor Screen Glass */}
                  <rect x="345" y="210" width="110" height="90" rx="20" fill={theme.id === "midnight" ? "#050B14" : "#1E293B"} stroke={theme.charStroke} strokeWidth="2" />
                  <path d="M 352 220 Q 380 215 420 220" stroke="rgba(255,255,255,0.25)" strokeWidth="3" strokeLinecap="round" />

                  {/* Side Bolts */}
                  <rect x="320" y="240" width="10" height="30" rx="4" fill={theme.charStroke} />
                  <rect x="470" y="240" width="10" height="30" rx="4" fill={theme.charStroke} />

                  {/* Digital LED Eyes */}
                  {isBlinking ? (
                    <>
                      <rect x="366" y="252" width="22" height="4" rx="2" fill="#38BDF8" filter="drop-shadow(0 0 6px #38BDF8)" />
                      <rect x="412" y="252" width="22" height="4" rx="2" fill="#38BDF8" filter="drop-shadow(0 0 6px #38BDF8)" />
                    </>
                  ) : activeScene.characterState === "loyal" || activeScene.characterState === "proud" ? (
                    <>
                      <path d="M 368 258 Q 378 244 388 258" fill="none" stroke="#38BDF8" strokeWidth="4" strokeLinecap="round" filter="drop-shadow(0 0 6px #38BDF8)" />
                      <path d="M 412 258 Q 422 244 432 258" fill="none" stroke="#38BDF8" strokeWidth="4" strokeLinecap="round" filter="drop-shadow(0 0 6px #38BDF8)" />
                    </>
                  ) : (
                    <>
                      <rect x="368" y="245" width="18" height="20" rx="5" fill="#38BDF8" filter="drop-shadow(0 0 6px #38BDF8)" />
                      <rect x="414" y="245" width="18" height="20" rx="5" fill="#38BDF8" filter="drop-shadow(0 0 6px #38BDF8)" />
                    </>
                  )}

                  {/* Digital LED Mouth */}
                  <rect x="388" y="278" width="24" height={Math.max(4, talkMouth * 0.45)} rx="2" fill="#38BDF8" filter="drop-shadow(0 0 4px #38BDF8)" />
                </g>
              );
            } else if (charType === "ghost") {
              // =================== 6. GHOST (BÉ MA BỒNG BỀNH) ===================
              const ghostFloat = Math.sin(currentFrame * 0.12) * 14;
              const ghostSway = Math.sin(currentFrame * 0.08) * 6;
              return (
                <g id="character-ghost" transform={`translate(${ghostSway}, ${ghostFloat - 40})`}>
                  {/* Floating Halo */}
                  <ellipse cx="400" cy="188" rx="26" ry="7" fill="none" stroke="#FDE047" strokeWidth="3" filter="drop-shadow(0 0 8px #FDE047)" />

                  {/* Flowing Ghost Sheet */}
                  <path
                    d="M 335 320 Q 335 200 400 200 Q 465 200 465 320 C 478 380 475 440 465 465 Q 450 450 435 465 Q 420 450 405 465 Q 390 450 375 465 Q 360 450 345 465 C 330 440 322 380 335 320 Z"
                    fill={theme.charHeadFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth}
                    filter={theme.charHeadFilter}
                  />

                  {/* Stubby Ghost Arms */}
                  <path d="M 334 335 Q 305 345 320 365 Q 336 365 338 350" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                  <path d="M 466 335 Q 495 345 480 365 Q 464 365 462 350" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />

                  {/* Kawaii Eyes */}
                  {!isBlinking ? (
                    <>
                      <ellipse cx="380" cy="265" rx="7" ry="11" fill={theme.charStroke} />
                      <circle cx="377" cy="261" r="3" fill="#FFFFFF" />
                      <ellipse cx="420" cy="265" rx="7" ry="11" fill={theme.charStroke} />
                      <circle cx="417" cy="261" r="3" fill="#FFFFFF" />
                    </>
                  ) : (
                    <>
                      <path d="M 373 265 Q 380 258 387 265" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                      <path d="M 413 265 Q 420 258 427 265" fill="none" stroke={theme.charStroke} strokeWidth="3.5" strokeLinecap="round" />
                    </>
                  )}

                  {/* Cheeks */}
                  <ellipse cx="364" cy="280" rx="10" ry="6" fill={theme.charBlushColor} />
                  <ellipse cx="436" cy="280" rx="10" ry="6" fill={theme.charBlushColor} />

                  {/* Ghost Mouth */}
                  <ellipse cx="400" cy="285" rx="7" ry={Math.max(4, talkMouth * 0.45)} fill={theme.charMouthFill} stroke={theme.charStroke} strokeWidth="2.5" />

                  {/* Magic Sparkles */}
                  <text x="315" y="240" fontSize="16" fill="#FDE047" opacity="0.8">✨</text>
                  <text x="470" y="250" fontSize="14" fill="#FDE047" opacity="0.8">✦</text>
                </g>
              );
            } else {
              // =================== 1. STICKMAN (NGƯỜI QUE) ===================
              // Brutalist Design applied to ALL themes with preserved theme color palette
              const tieFill = theme.id === "brutalism" ? "#000000" : (theme.id === "midnight" || theme.id === "pixel" || theme.id === "whiteboard" ? "#0A0E17" : theme.charStroke);
              const tieStroke = theme.id === "brutalism" ? "#FFE600" : (theme.id === "midnight" ? "#F4E2BB" : (theme.id === "whiteboard" ? "#FDE047" : theme.charScarfFill));

              const glassesFill = theme.id === "brutalism" ? "#000000" : (theme.id === "midnight" || theme.id === "pixel" || theme.id === "whiteboard" ? "#0A0E17" : theme.charStroke);
              const glassesStroke = theme.id === "brutalism" ? "#FFE600" : (theme.id === "midnight" ? "#F4E2BB" : (theme.id === "whiteboard" ? "#FDE047" : theme.charScarfFill));

              return (
                <g id="character-stickman">
                  {/* Sitting Legs */}
                  <line x1="380" y1="440" x2="360" y2="480" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                  <line x1="360" y1="480" x2="340" y2="505" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                  <ellipse cx="335" cy="507" rx="14" ry="7" fill={theme.charStroke} />

                  <line x1="420" y1="440" x2="440" y2="480" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                  <line x1="440" y1="480" x2="460" y2="505" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                  <ellipse cx="465" cy="507" rx="14" ry="7" fill={theme.charStroke} />

                  {/* Torso */}
                  <line x1="400" y1="330" x2="400" y2="440" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth + 2} strokeLinecap="round" />

                  {/* Sharp Brutalist Necktie (Styled with Theme Colors) */}
                  <polygon
                    points="392,335 408,335 412,400 400,420 388,400"
                    fill={tieFill}
                    stroke={tieStroke}
                    strokeWidth="2.5"
                  />
                  <polygon
                    points="394,330 406,330 408,338 392,338"
                    fill={tieFill}
                    stroke={tieStroke}
                    strokeWidth="2"
                  />

                  {/* Arms & Gestures */}
                  {(() => {
                    if (activeScene.characterState === "reflecting") {
                      return (
                        <>
                          <line x1="380" y1="340" x2="330" y2="380" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="330" y1="380" x2="340" y2="430" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="420" y1="340" x2="445" y2="355" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="445" y1="355" x2="425" y2="295" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <circle cx="423" cy="292" r="8" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                        </>
                      );
                    } else if (activeScene.characterState === "loyal") {
                      return (
                        <>
                          <line x1="380" y1="340" x2="370" y2="375" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="370" y1="375" x2="400" y2="380" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="420" y1="340" x2="430" y2="375" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="430" y1="375" x2="400" y2="380" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <g transform="translate(388, 365) scale(1.2)">
                            <rect x="0" y="8" width="20" height="16" rx="3" fill="#F4A261" stroke={theme.charStroke} strokeWidth="2" />
                            <path d="M 4 8 A 6 6 0 0 1 16 8" fill="none" stroke={theme.charStroke} strokeWidth="2.5" />
                            <circle cx="10" cy="15" r="2.5" fill={theme.charStroke} />
                          </g>
                        </>
                      );
                    } else if (activeScene.characterState === "sad") {
                      return (
                        <>
                          <line x1="380" y1="340" x2="350" y2="390" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="350" y1="390" x2="340" y2="440" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="420" y1="340" x2="450" y2="390" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="450" y1="390" x2="460" y2="440" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                        </>
                      );
                    } else {
                      return (
                        <>
                          <line x1="380" y1="340" x2="355" y2="370" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="355" y1="370" x2="388" y2="360" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <circle cx="390" cy="360" r="8" fill={theme.charHeadFill} stroke={theme.charStroke} strokeWidth="3" />
                          <line x1="420" y1="340" x2="460" y2="375" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                          <line x1="460" y1="375" x2="450" y2="425" stroke={theme.charStroke} strokeWidth={theme.charStrokeWidth} strokeLinecap="round" />
                        </>
                      );
                    }
                  })()}

                  {/* HEAD */}
                  <circle
                    cx="400"
                    cy="255"
                    r="52"
                    fill={theme.charHeadFill}
                    stroke={theme.charStroke}
                    strokeWidth={theme.charStrokeWidth}
                    filter={theme.charHeadFilter}
                  />

                  {/* Hair Strands */}
                  <path d="M 390 203 Q 400 180 415 204" fill="none" stroke={theme.charStroke} strokeWidth="5" strokeLinecap="round" />
                  <path d="M 405 203 Q 420 185 425 206" fill="none" stroke={theme.charStroke} strokeWidth="4" strokeLinecap="round" />

                  {/* Brutalist Sunglasses across ALL themes */}
                  <g transform="translate(365, 238)">
                    <polygon points="0,0 32,0 28,18 4,18" fill={glassesFill} stroke={glassesStroke} strokeWidth="2.5" />
                    <line x1="32" y1="8" x2="38" y2="8" stroke={glassesFill} strokeWidth="3" />
                    <polygon points="38,0 70,0 66,18 42,18" fill={glassesFill} stroke={glassesStroke} strokeWidth="2.5" />
                    <line x1="6" y1="3" x2="20" y2="15" stroke="rgba(255,255,255,0.35)" strokeWidth="1.8" strokeLinecap="round" />
                    <line x1="44" y1="3" x2="58" y2="15" stroke="rgba(255,255,255,0.35)" strokeWidth="1.8" strokeLinecap="round" />
                  </g>

                  {/* Blushing */}
                  <circle cx="372" cy="264" r="8" fill={theme.charBlushColor} />
                  <circle cx="428" cy="264" r="8" fill={theme.charBlushColor} />

                  {/* Talking Mouth */}
                  {activeScene.characterState === "sad" ? (
                    <path d="M 388 280 Q 400 270 412 280" fill="none" stroke={theme.charStroke} strokeWidth="4" strokeLinecap="round" />
                  ) : (
                    <ellipse
                      cx="400"
                      cy="276"
                      rx="8"
                      ry={Math.max(3, talkMouth * 0.45)}
                      fill={theme.charMouthFill}
                      stroke={theme.charStroke}
                      strokeWidth="3"
                    />
                  )}

                  {/* Heart on chest */}
                  {(activeScene.characterState === "peace" || activeScene.characterState === "proud") && (
                    <g transform={`translate(385, 360) scale(${1 + Math.sin(currentFrame * 0.3) * 0.15})`}>
                      <path
                        d="M 12 5 A 4 4 0 0 0 4 5 Q 4 10 12 18 Q 20 10 20 5 A 4 4 0 0 0 12 5"
                        fill="#E63946"
                        stroke="#FFFFFF"
                        strokeWidth="2"
                        filter="drop-shadow(0 0 10px rgba(230, 57, 70, 0.8))"
                      />
                    </g>
                  )}
                </g>
              );
            }
          })()}
          {action === 'heart' && <text x="490" y={270 - Math.sin(actionTime * 0.06) * 10} fontSize="52" fill="#E07A5F">♥</text>}
          {action === 'think' && <text x="475" y="210" fontSize="42" fill={theme.charStroke}>?</text>}
          {action === 'celebrate' && <text x="300" y="190" fontSize="44" fill="#F4A261">✦ ✧ ✦</text>}
          {action === 'breathe' && <circle cx="400" cy="335" r={112 + Math.sin(actionTime * 0.05) * 16}
            fill="none" stroke="#81B29A" opacity="0.4" strokeWidth="4" />}
          </g>
        </svg>
      </div>

      {/* FLOATING CARD / NOTE (DYNAMICALLY ORBITING AROUND SUBJECT) */}
      <div
        style={{
          position: "absolute",
          top: posConfig.top,
          right: posConfig.right,
          left: posConfig.left,
          width: noteWidth,
          opacity: sceneVisible ? 1 : 0,
          transform: `${posConfig.isCenter ? "translateX(-50%) " : ""}scale(${noteSpring}) rotate(${activeScene.note.rotation || posConfig.rot}deg)`,
          transformOrigin: posConfig.origin,
          background: theme.cardBg(activeScene.note.color),
          borderRadius: theme.cardRadius,
          padding: isSquare ? "14px 16px" : "18px 20px",
          boxShadow: theme.cardShadow,
          border: theme.cardBorder,
          maxHeight: isHorizontal ? 210 : isSquare ? 160 : 170,
          overflow: "hidden",
          zIndex: 25,
        }}
      >
        {/* Decorative Tape / Pin / Strip */}
        <div
          style={{
            position: "absolute",
            top: -14,
            left: "50%",
            transform: "translateX(-50%)",
            width: 90,
            height: 26,
            background: theme.cardTapeBg,
            borderRadius: theme.id === "pixel" || theme.id === "brutalism" ? 0 : 3,
            boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
          }}
        />

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 10,
          }}
        >
          <span style={{ fontSize: isSquare ? 18 : 21, fontWeight: 900, color: theme.cardTitleColor }}>
            {activeScene.note.title}
          </span>
          <span
            style={{
              fontSize: isSquare ? 11 : 13,
              fontWeight: 800,
              color: theme.cardTagColor,
              background: theme.cardTagBg,
              padding: "4px 12px",
              borderRadius: theme.id === "pixel" || theme.id === "brutalism" ? 0 : 12,
              border: theme.id === "brutalism" ? "2px solid #000" : "none",
            }}
          >
            {activeScene.note.tag}
          </span>
        </div>

        <div
          style={{
            fontSize: isSquare ? 15 : 18,
            lineHeight: 1.5,
            color: theme.cardBodyColor,
            fontWeight: 700,
            whiteSpace: "pre-line",
            borderTop: theme.cardDivider,
            paddingTop: 12,
          }}
        >
          {activeScene.note.body}
        </div>
      </div>

      {/* TWO-TIER KINETIC TYPOGRAPHY SECTION */}
      <div
        style={{
          position: "absolute",
          top: typoTop,
          bottom: typoBottom,
          left: typoLeft,
          right: typoRight,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: isSquare ? 18 : 28,
          zIndex: 30,
        }}
      >
        {/* Tier 1: Spoken Sentence Context Line */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            alignItems: "center",
            gap: isSquare ? "8px 12px" : "12px 18px",
            maxWidth: isHorizontal ? "1200px" : "920px",
          }}
        >
          {(sceneVisible ? activeScene.leadWords.slice(0, 10) : []).map((w, idx) => {
            const isSpeakingNow = currentFrame >= w.start && currentFrame < w.end;
            const hasSpoken = currentFrame > w.end;
            const wordDelay = Math.max(0, currentFrame - w.start);

            const wordSpring = spring({
              frame: wordDelay,
              fps,
              config: { damping: 10, stiffness: 220 },
            });

            let wordColor = theme.leadPastColor;
            let wordBg = undefined as string | undefined;
            let wordBorder = undefined as string | undefined;
            let wordPadding = undefined as string | undefined;
            let wordRadius = undefined as number | string | undefined;
            let scale = 1;
            let fontWeight = 800;
            let shadow = "none";

            if (isSpeakingNow) {
              wordColor = theme.leadActiveColor;
              wordBg = theme.leadActiveBg;
              wordBorder = theme.leadActiveBorder;
              wordPadding = theme.leadActivePadding;
              wordRadius = theme.leadActiveRadius;
              scale = theme.leadActiveScale;
              fontWeight = 950;
              shadow = theme.leadActiveShadow;
            } else if (hasSpoken) {
              wordColor = theme.leadPastColor;
              scale = 1.05;
              fontWeight = 850;
            } else {
              wordColor = theme.leadFutureColor;
            }

            return (
              <span
                key={idx}
                style={{
                  fontSize: leadFontSize,
                  fontWeight,
                  color: wordColor,
                  background: wordBg,
                  border: wordBorder,
                  padding: wordPadding,
                  borderRadius: wordRadius,
                  transform: `scale(${isSpeakingNow ? wordSpring * scale : scale})`,
                  display: "inline-block",
                  transition: "transform 0.12s ease",
                  letterSpacing: theme.id === "pixel" ? 3 : 0.5,
                  textShadow: shadow,
                  textTransform: theme.id === "brutalism" ? "uppercase" : "none",
                }}
              >
                {w.text}
              </span>
            );
          })}
        </div>

        {/* Tier 2: GRAND KINETIC HIGHLIGHT PILL BADGE */}
        {isKeyActive && (
          <div
            style={{
              transform: `scale(${keySpring}) rotate(${Math.sin(currentFrame * 0.25) * 1.8}deg)`,
              display: "flex",
              alignItems: "center",
              gap: 16,
              maxWidth: width * 0.92,
              boxSizing: 'border-box',
              padding: isSquare ? "12px 26px" : "18px 36px",
              borderRadius: theme.keyRadius,
              backgroundColor: activeScene.keyPhrase.pillBg,
              boxShadow: theme.keyShadow,
              border: theme.keyBorder,
            }}
          >
            <span style={{ fontSize: keyIconSize }}>{activeScene.keyPhrase.icon}</span>
            <span
              style={{
                fontSize: Math.min(keyFontSize, (width * 0.82 - 120) / Math.max(1, activeScene.keyPhrase.text.length * 0.58)),
                minWidth: 0,
                overflowWrap: 'anywhere',
                textAlign: 'center',
                fontWeight: 950,
                color: activeScene.keyPhrase.textColor,
                letterSpacing: 2,
                textTransform: "uppercase",
                textShadow: "0 2px 6px rgba(0,0,0,0.3)",
              }}
            >
              {activeScene.keyPhrase.text}
            </span>
          </div>
        )}

        {/* Audio Waveform Equalizer */}
        <div
          style={{
            marginTop: isSquare ? 10 : 20,
            display: "flex",
            alignItems: "center",
            gap: 8,
            height: isSquare ? 30 : 42,
          }}
        >
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14].map((bar) => {
            const h = interpolate(
              Math.sin(currentFrame * 0.4 + bar * 0.65),
              [-1, 1],
              timedDialogue && !speakingNow ? [3, 3] : isSquare ? [6, 26] : [8, 38]
            );
            const col = theme.eqColors[bar % theme.eqColors.length];
            return (
              <div
                key={bar}
                style={{
                  width: theme.eqRadius === 0 ? 8 : 6,
                  height: h,
                  borderRadius: theme.eqRadius,
                  backgroundColor: col,
                  boxShadow: theme.eqShadow,
                  border: theme.id === "brutalism" ? "1.5px solid #000" : "none",
                }}
              />
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
