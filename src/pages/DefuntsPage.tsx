import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, Button, DataLoader, ErrorMessage, Input } from "@/components/ui";
import { useIndividuals } from "@/hooks";
import { Users, Search } from "lucide-react";

export default function DefuntsPage() {
  const { data: individuals, loading, error, refetch } = useIndividuals();
  const [searchQuery, setSearchQuery] = useState("");

  // Filter to only deceased
  const deceased = individuals?.filter((ind) => ind.role === "deceased") ?? [];
  const filtered = deceased.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4">
      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Rechercher</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher par nom..."
              className="pl-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Défunts enregistrés</CardTitle>
            {error && <ErrorMessage error={error} onRetry={refetch} />}
          </div>
        </CardHeader>
        <CardContent>
          <DataLoader
            loading={loading}
            error={error}
            data={filtered}
            onRetry={refetch}
            emptyState={{
              icon: <Users className="h-8 w-8" />,
              title: searchQuery ? "Aucun défunt trouvé" : "Aucun défunt",
              description: searchQuery
                ? "Aucun résultat ne correspond à votre recherche"
                : "Créez un premier enregistrement de défunt",
            }}
          >
            <div className="space-y-2">
              {filtered.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between p-4 border rounded hover:bg-accent transition"
                >
                  <div className="flex-1">
                    <p className="font-medium">{d.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {d.email && `${d.email}`}
                      {d.phone && `${d.email ? " • " : ""}${d.phone}`}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm">
                    Détails
                  </Button>
                </div>
              ))}
            </div>
          </DataLoader>
        </CardContent>
      </Card>

      {/* Stats */}
      {!loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground font-medium">Total défunts</p>
                <p className="text-2xl font-bold">{deceased.length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-medium">Avec contact</p>
                <p className="text-2xl font-bold">{deceased.filter((d) => d.email || d.phone).length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
