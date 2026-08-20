import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CemeteryMap } from "@/components/map/CemeteryMap";
import { mockCemeteryMap } from "@/mocks/cemetery-map";
import { PlotMapDTO } from "@/types/bindings";

export default function EmplacementsPage() {
  const [selectedPlotId, setSelectedPlotId] = useState<number | null>(null);
  const [selectedPlot, setSelectedPlot] = useState<PlotMapDTO | null>(null);

  const handlePlotSelect = (plot: PlotMapDTO | null) => {
    if (plot === null) {
      setSelectedPlotId(null);
      setSelectedPlot(null);
    } else {
      setSelectedPlotId(plot.id);
      setSelectedPlot(plot);
    }
  };

  return (
    <div className="space-y-4 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {mockCemeteryMap.name}
          </h1>
          {mockCemeteryMap.commune && (
            <p className="text-sm text-gray-600">
              Commune de {mockCemeteryMap.commune}
            </p>
          )}
        </div>
      </div>

      {/* Map and details container */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0">
        {/* Map (main content) */}
        <Card className="lg:col-span-3 flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Plan du cimetière (MVP-14)</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Mock data – Intégration réelle disponible après MVP-10 (backend)
            </p>
          </CardHeader>
          <CardContent className="flex-1 overflow-hidden">
            <CemeteryMap
              data={mockCemeteryMap}
              onPlotSelect={handlePlotSelect}
              selectedPlotId={selectedPlotId}
            />
          </CardContent>
        </Card>

        {/* Details sidebar */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Informations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {selectedPlot ? (
              <>
                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Emplacement sélectionné
                  </p>
                  <p className="text-base font-semibold mt-1">
                    {selectedPlot.section}/{selectedPlot.row}/{selectedPlot.number}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Statut
                  </p>
                  <p className="mt-1">
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-semibold text-white ${
                        selectedPlot.status === "available"
                          ? "bg-green-600"
                          : selectedPlot.status === "occupied"
                          ? "bg-blue-600"
                          : selectedPlot.status === "reserved"
                          ? "bg-orange-600"
                          : "bg-gray-600"
                      }`}
                    >
                      {selectedPlot.status === "available"
                        ? "Libre"
                        : selectedPlot.status === "occupied"
                        ? "Occupé"
                        : selectedPlot.status === "reserved"
                        ? "Réservé"
                        : "Indisponible"}
                    </span>
                  </p>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Capacité
                  </p>
                  <p className="mt-1">{selectedPlot.capacity} place(s)</p>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Occupé
                  </p>
                  <p className="mt-1">{selectedPlot.occupied_count} personne(s)</p>
                </div>

                <div>
                  <p className="text-xs text-muted-foreground font-medium">
                    Concession(s)
                  </p>
                  <p className="mt-1">{selectedPlot.concession_count}</p>
                </div>

                <button
                  onClick={() => {
                    setSelectedPlotId(null);
                    setSelectedPlot(null);
                  }}
                  className="w-full mt-4 px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded text-xs font-medium text-gray-900 transition"
                >
                  Désélectionner
                </button>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p className="text-sm">Sélectionnez un emplacement sur le plan</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer stats */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div>
              <p className="text-xs text-muted-foreground font-medium">
                Secteurs
              </p>
              <p className="text-xl font-bold">{mockCemeteryMap.section_count}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">
                Rangées max
              </p>
              <p className="text-xl font-bold">{mockCemeteryMap.max_row}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">
                Capacité totale
              </p>
              <p className="text-xl font-bold">{mockCemeteryMap.total_capacity}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Occupés</p>
              <p className="text-xl font-bold text-blue-600">
                {mockCemeteryMap.occupied_count}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Libres</p>
              <p className="text-xl font-bold text-green-600">
                {mockCemeteryMap.available_count}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
