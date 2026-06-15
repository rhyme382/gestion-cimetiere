import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Building2, FileText, Users, Bell } from "lucide-react";

const stats = [
  { label: "Cimetières", value: "—", icon: Building2, color: "text-blue-600" },
  { label: "Concessions", value: "—", icon: FileText, color: "text-green-600" },
  { label: "Défunts", value: "—", icon: Users, color: "text-purple-600" },
  { label: "Alertes actives", value: "—", icon: Bell, color: "text-orange-600" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className={`h-4 w-4 ${color}`} />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Activité récente</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Aucune activité récente. Les données seront affichées ici une fois le backend complet (MVP-10/11).</p>
        </CardContent>
      </Card>
    </div>
  );
}
