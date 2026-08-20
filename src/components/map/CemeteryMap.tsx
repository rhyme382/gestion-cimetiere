import { useState } from "react";
import { CemeteryMapDTO, PlotMapDTO } from "@/types/bindings";
import { MapPin } from "lucide-react";

// Grid rendering constants (from MVP-07)
const PLOT_WIDTH = 50;
const PLOT_HEIGHT = 50;
const PLOT_GAP = 2;
const SECTION_SPACING = 80;
const ROW_SPACING = 60;

interface CemeteryMapProps {
  data: CemeteryMapDTO;
  onPlotSelect?: (plot: PlotMapDTO | null) => void;
  selectedPlotId?: number | null;
}

export function CemeteryMap({
  data,
  onPlotSelect,
  selectedPlotId,
}: CemeteryMapProps) {
  const [hoveredPlotId, setHoveredPlotId] = useState<number | null>(null);

  // Group plots by section and row
  const groupedPlots = groupPlotsBySection(data.plots);

  // Calculate canvas dimensions
  const sections = Object.keys(groupedPlots).sort();
  const sectionCount = sections.length;
  const maxRowPerSection = Math.max(
    ...Object.values(groupedPlots).map((rows) => Object.keys(rows).length)
  );
  const maxPlotsPerRow = Math.max(
    ...data.plots
      .filter((p) => p.section && p.row)
      .map((p) => p.number || 0)
  );

  const svgWidth =
    sectionCount * (SECTION_SPACING + (maxPlotsPerRow * (PLOT_WIDTH + PLOT_GAP)));
  const svgHeight = maxRowPerSection * (ROW_SPACING + PLOT_HEIGHT) + 100;

  // Get color for plot status
  const getPlotColor = (status: string): string => {
    switch (status) {
      case "available":
        return "#10b981"; // green
      case "occupied":
        return "#3b82f6"; // blue
      case "reserved":
        return "#f59e0b"; // orange
      case "unavailable":
        return "#9ca3af"; // gray
      default:
        return "#e5e7eb"; // light gray
    }
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Legend */}
      <div className="mb-4 flex gap-4 flex-wrap text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#10b981" }} />
          <span>Libre</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#3b82f6" }} />
          <span>Occupé</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#f59e0b" }} />
          <span>Réservé</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: "#9ca3af" }} />
          <span>Indisponible</span>
        </div>
      </div>

      {/* Canvas wrapper with scrolling */}
      <div className="flex-1 border rounded-lg overflow-auto bg-slate-50">
        <svg
          width={svgWidth}
          height={svgHeight}
          className="block"
          style={{ minWidth: "100%", minHeight: "100%" }}
        >
          {/* Render plots per section */}
          {sections.map((sectionKey, sectionIdx) => {
            const rows = groupedPlots[sectionKey];
            const sectionX = sectionIdx * SECTION_SPACING + 40;

            return (
              <g key={`section-${sectionKey}`}>
                {/* Section label */}
                <text
                  x={sectionX}
                  y={25}
                  className="text-xs font-bold"
                  textAnchor="start"
                  fill="#1f2937"
                >
                  Secteur {sectionKey}
                </text>

                {/* Rows */}
                {Object.entries(rows)
                  .sort(([rowA], [rowB]) => Number(rowA) - Number(rowB))
                  .map(([rowKey, plots]) => {
                    const rowNum = Number(rowKey);
                    const rowY = rowNum * ROW_SPACING + 40;

                    return (
                      <g key={`row-${sectionKey}-${rowKey}`}>
                        {/* Row label */}
                        <text
                          x={sectionX - 30}
                          y={rowY + PLOT_HEIGHT / 2 + 4}
                          className="text-xs font-semibold"
                          textAnchor="end"
                          fill="#4b5563"
                        >
                          L{rowNum}
                        </text>

                        {/* Plots in row */}
                        {plots
                          .sort((a, b) => (a.number || 0) - (b.number || 0))
                          .map((plot, idx) => {
                            const plotX = sectionX + idx * (PLOT_WIDTH + PLOT_GAP);
                            const plotY = rowY;
                            const isSelected = selectedPlotId === plot.id;
                            const isHovered = hoveredPlotId === plot.id;

                            return (
                              <g
                                key={`plot-${plot.id}`}
                                onMouseEnter={() => setHoveredPlotId(plot.id)}
                                onMouseLeave={() => setHoveredPlotId(null)}
                                onClick={() => onPlotSelect?.(plot)}
                                style={{ cursor: "pointer" }}
                              >
                                {/* Plot rectangle */}
                                <rect
                                  x={plotX}
                                  y={plotY}
                                  width={PLOT_WIDTH}
                                  height={PLOT_HEIGHT}
                                  fill={getPlotColor(plot.status)}
                                  stroke={
                                    isSelected
                                      ? "#1e40af"
                                      : isHovered
                                      ? "#374151"
                                      : "#d1d5db"
                                  }
                                  strokeWidth={isSelected ? 3 : isHovered ? 2 : 1}
                                  rx={2}
                                  opacity={isHovered ? 0.9 : 0.8}
                                />

                                {/* Plot number (if available) */}
                                {plot.number && (
                                  <text
                                    x={plotX + PLOT_WIDTH / 2}
                                    y={plotY + PLOT_HEIGHT / 2 + 4}
                                    className="text-xs font-bold pointer-events-none"
                                    textAnchor="middle"
                                    fill="white"
                                    style={{ textShadow: "0 1px 2px rgba(0,0,0,0.5)" }}
                                  >
                                    {plot.number}
                                  </text>
                                )}

                                {/* Tooltip on hover */}
                                {isHovered && (
                                  <g>
                                    <rect
                                      x={plotX + PLOT_WIDTH / 2 - 50}
                                      y={plotY - 35}
                                      width={100}
                                      height={30}
                                      fill="rgba(0, 0, 0, 0.9)"
                                      rx={4}
                                      pointerEvents="none"
                                    />
                                    <text
                                      x={plotX + PLOT_WIDTH / 2}
                                      y={plotY - 20}
                                      className="text-xs font-semibold pointer-events-none"
                                      textAnchor="middle"
                                      fill="white"
                                    >
                                      {sectionKey}/{rowNum}/{plot.number}
                                    </text>
                                    <text
                                      x={plotX + PLOT_WIDTH / 2}
                                      y={plotY - 10}
                                      className="text-xs pointer-events-none"
                                      textAnchor="middle"
                                      fill="#d1d5db"
                                    >
                                      {plot.status === "available"
                                        ? "Libre"
                                        : plot.status === "occupied"
                                        ? "Occupé"
                                        : "Réservé"}
                                    </text>
                                  </g>
                                )}
                              </g>
                            );
                          })}
                      </g>
                    );
                  })}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Stats footer */}
      {selectedPlotId === null && (
        <div className="mt-4 grid grid-cols-4 gap-4 text-center text-xs">
          <div>
            <div className="font-semibold text-lg">{data.total_capacity}</div>
            <div className="text-muted-foreground">Capacité</div>
          </div>
          <div>
            <div className="font-semibold text-lg text-blue-600">
              {data.occupied_count}
            </div>
            <div className="text-muted-foreground">Occupés</div>
          </div>
          <div>
            <div className="font-semibold text-lg text-green-600">
              {data.available_count}
            </div>
            <div className="text-muted-foreground">Libres</div>
          </div>
          <div>
            <div className="font-semibold text-lg">{data.section_count}</div>
            <div className="text-muted-foreground">Secteurs</div>
          </div>
        </div>
      )}

      {/* Selected plot info */}
      {selectedPlotId !== null && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-600" />
              <span>
                Emplacement sélectionné : ID {selectedPlotId}
              </span>
            </div>
            <button
              onClick={() => onPlotSelect?.(null)}
              className="text-blue-600 hover:text-blue-800 text-xs font-medium"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper function to group plots by section and row
function groupPlotsBySection(
  plots: PlotMapDTO[]
): Record<string, Record<number, PlotMapDTO[]>> {
  const grouped: Record<string, Record<number, PlotMapDTO[]>> = {};

  plots.forEach((plot) => {
    const section = plot.section || "?";
    const row = plot.row || 0;

    if (!grouped[section]) {
      grouped[section] = {};
    }
    if (!grouped[section][row]) {
      grouped[section][row] = [];
    }
    grouped[section][row].push(plot);
  });

  return grouped;
}
