import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useState } from "react";

export default function RecherchePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) setSearchParams({ q: query.trim() });
  }

  const currentQuery = searchParams.get("q");

  return (
    <div className="space-y-4 max-w-2xl">
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Rechercher un défunt, une concession, un emplacement…"
            className="pl-9"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
      </form>

      {currentQuery ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Résultats pour « {currentQuery} »</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">La recherche sera disponible après MVP-11 (commandes Tauri search_individuals).</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Saisissez un terme pour rechercher dans tous les registres.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
