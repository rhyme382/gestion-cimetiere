import { Card, CardContent } from "@/components/ui/card";
import { MapPin } from "lucide-react";

export default function EmplacementsPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <MapPin className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p className="text-sm font-medium">Liste des emplacements</p>
          <p className="text-xs text-muted-foreground mt-1">Disponible après implémentation des commandes Tauri (MVP-10)</p>
        </CardContent>
      </Card>
    </div>
  );
}
