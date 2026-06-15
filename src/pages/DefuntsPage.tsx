import { Card, CardContent } from "@/components/ui/card";
import { Users } from "lucide-react";

export default function DefuntsPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Users className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p className="text-sm font-medium">Registre des défunts</p>
          <p className="text-xs text-muted-foreground mt-1">Disponible après implémentation des commandes Tauri (MVP-11)</p>
        </CardContent>
      </Card>
    </div>
  );
}
