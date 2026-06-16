import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MapPin } from "lucide-react";
import { PlotDTO } from "@/types/bindings";

interface PlotViewerProps {
  plot: PlotDTO | null | undefined;
  cemeteryName?: string;
  size?: "sm" | "md";
}

export function PlotViewer({ plot, cemeteryName, size = "sm" }: PlotViewerProps) {
  if (!plot) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Localisation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Aucun emplacement associé</p>
        </CardContent>
      </Card>
    );
  }

  const svgSize = size === "sm" ? 200 : 300;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <MapPin className="h-4 w-4" />
          Localisation
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center">
        {/* Mini SVG visualization */}
        <svg
          width={svgSize}
          height={160}
          viewBox="0 0 200 160"
          className="border rounded bg-slate-50 mb-4"
        >
          {/* Render section label */}
          <text x={10} y={20} className="text-xs font-bold" fill="#1f2937">
            {plot.section || "—"}
          </text>

          {/* Row label */}
          <text x={10} y={60} className="text-xs font-semibold" fill="#4b5563">
            Rangée {plot.row}
          </text>

          {/* Plot rectangle (centered) */}
          <rect
            x={100}
            y={70}
            width={60}
            height={60}
            fill="#3b82f6"
            stroke="#1e40af"
            strokeWidth={2}
            rx={4}
          />

          {/* Plot number */}
          <text
            x={130}
            y={110}
            className="text-sm font-bold"
            textAnchor="middle"
            fill="white"
          >
            {plot.number}
          </text>
        </svg>

        {/* Details */}
        <div className="w-full text-center space-y-1">
          {cemeteryName && (
            <p className="text-xs text-muted-foreground">{cemeteryName}</p>
          )}
          <p className="text-xs font-medium">
            {plot.section}
            {plot.row && <> / Rangée {plot.row}</>} / #{plot.number}
          </p>
          <p className="text-xs text-muted-foreground">
            Capacité : {plot.capacity}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
