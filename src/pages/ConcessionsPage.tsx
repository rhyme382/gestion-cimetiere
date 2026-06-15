import { Card, CardContent } from "@/components/ui/card";
import { FileText } from "lucide-react";

export default function ConcessionsPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="h-12 w-12 text-muted-foreground/30 mb-4" />
          <p className="text-sm font-medium">Liste des concessions</p>
          <p className="text-xs text-muted-foreground mt-1">Disponible après implémentation des commandes Tauri (MVP-10/11)</p>
        </CardContent>
      </Card>
    </div>
  );
}
