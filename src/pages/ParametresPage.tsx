import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings } from "lucide-react";

export default function ParametresPage() {
  return (
    <div className="space-y-4 max-w-2xl">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">Paramètres de l'application</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">La configuration communale sera disponible dans une version ultérieure (MVP-21+).</p>
        </CardContent>
      </Card>
    </div>
  );
}
