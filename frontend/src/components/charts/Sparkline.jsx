import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import { useTheme } from "../../app/ThemeContext.jsx";

const COBALT = { light: "#2f55c8", dark: "#7091ff" };

export default function Sparkline({ data, dataKey = "value", color, height = 36 }) {
  const { theme } = useTheme();
  if (!data || data.length < 2) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color ?? COBALT[theme]}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
