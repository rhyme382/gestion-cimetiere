import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button, DataLoader, Input } from "@/components/ui";
import { useSearchIndividuals, useConcessions } from "@/hooks";
import { Search, Users, FileText } from "lucide-react";
import { useState } from "react";

export default function RecherchePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const currentQuery = searchParams.get("q");

  const { data: individuals, loading: indLoading, error: indError } = useSearchIndividuals(currentQuery);
  const { data: allConcessions, loading: conLoading } = useConcessions();

  // Filter concessions by cemetery_id matching query if query is numeric
  const matchedConcessions = currentQuery && !isNaN(Number(currentQuery))
    ? allConcessions?.filter((c) => c.id === Number(currentQuery))
    : [];

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) setSearchParams({ q: query.trim() });
  }

  return (
    <div className="space-y-4">
      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recherche globale</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Rechercher par nom, ID de concession..."
                className="pl-9"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </div>
            <Button type="submit">Rechercher</Button>
          </form>
        </CardContent>
      </Card>

      {/* Results */}
      {currentQuery ? (
        <div className="space-y-4">
          {/* Individuals Results */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Users className="h-4 w-4" />
                Résultats — Personnes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataLoader
                loading={indLoading}
                error={indError}
                data={individuals}
                emptyState={{
                  title: "Aucune personne trouvée",
                  description: `Aucun résultat pour « ${currentQuery} »`,
                }}
              >
                <div className="space-y-2">
                  {individuals?.map((ind) => (
                    <div
                      key={ind.id}
                      className="flex items-center justify-between p-3 border rounded hover:bg-accent transition"
                    >
                      <div>
                        <p className="text-sm font-medium">{ind.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {ind.role === "deceased" && "Défunt"}
                          {ind.role === "concessionnaire" && "Concessionnaire"}
                          {ind.role === "heir" && "Ayant droit"}
                          {ind.role === "contact" && "Contact"}
                        </p>
                      </div>
                      <Button variant="ghost" size="sm">
                        Voir
                      </Button>
                    </div>
                  ))}
                </div>
              </DataLoader>
            </CardContent>
          </Card>

          {/* Concessions Results */}
          {!isNaN(Number(currentQuery)) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Résultats — Concessions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DataLoader
                  loading={conLoading}
                  error={null}
                  data={matchedConcessions}
                  emptyState={{
                    title: "Aucune concession trouvée",
                    description: `Pas de concession avec l'ID « ${currentQuery} »`,
                  }}
                >
                  <div className="space-y-2">
                    {matchedConcessions?.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center justify-between p-3 border rounded hover:bg-accent transition"
                      >
                        <div>
                          <p className="text-sm font-medium">Concession {c.id}</p>
                          <p className="text-xs text-muted-foreground">
                            Cimetière {c.cemetery_id} • {c.status}
                          </p>
                        </div>
                        <Button variant="ghost" size="sm">
                          Voir
                        </Button>
                      </div>
                    ))}
                  </div>
                </DataLoader>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Saisissez un nom pour rechercher des personnes ou un ID numérique pour les concessions.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
