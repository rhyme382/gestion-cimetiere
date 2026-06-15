import { Card, CardContent } from "@/components/ui/card";
import { Bell } from "lucide-react";

export default function AlertesPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Bell className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p className="text-sm font-medium">Centre d'alertes</p>
          <p className="text-xs text-muted-foreground mt-1">Disponible après implémentation des alertes d'échéance (MVP-16)</p>
        </CardContent>
      </Card>
    </div>
  );
}
