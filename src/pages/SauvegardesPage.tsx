import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, Button, DataLoader } from "@/components/ui";
import { useBackups } from "@/hooks";
import { HardDrive, Download, AlertTriangle, AlertCircle } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function SauvegardesPage() {
  const { backups, loading, error, creating, restoring, listBackups, createBackup, restoreBackup, reset } = useBackups();
  const [confirmRestore, setConfirmRestore] = useState<string | null>(null);

  useEffect(() => {
    listBackups();
  }, [listBackups]);

  async function handleCreateBackup() {
    await createBackup();
  }

  async function handleRestoreBackup(filename: string) {
    await restoreBackup(filename);
    setConfirmRestore(null);
  }

  return (
    <div className="space-y-6">
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="flex items-start gap-3 py-3">
            <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-red-800 mb-1">{error}</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => { reset(); listBackups(); }}
                className="text-xs h-6"
              >
                Réessayer
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Backup Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <HardDrive className="h-4 w-4" />
            Créer une sauvegarde
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground mb-4">
            Créez une sauvegarde complète de la base de données. Cette opération crée un fichier de secours que vous pouvez restaurer plus tard.
          </p>
          <Button
            onClick={handleCreateBackup}
            disabled={creating}
            className="w-full"
            variant="default"
          >
            {creating ? (
              <>
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                Création en cours...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Créer une sauvegarde
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Backups List Card */}
      <DataLoader
        loading={loading}
        error={null}
        data={backups}
        onRetry={listBackups}
      >
        {backups && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Sauvegardes disponibles</CardTitle>
            </CardHeader>
            <CardContent>
              {backups.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-8">
                  Aucune sauvegarde disponible. Créez-en une pour commencer.
                </p>
              ) : (
                <div className="space-y-2">
                  {backups.map((backup) => (
                    <div
                      key={backup.filename}
                      className="flex items-center justify-between p-3 border rounded bg-card hover:bg-accent/50 transition"
                    >
                      <div className="flex-1">
                        <p className="text-xs font-medium text-foreground">
                          {backup.filename}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Créée le {formatDate(backup.created_at)}
                          {backup.size && ` • ${(backup.size / 1024 / 1024).toFixed(2)} MB`}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        {confirmRestore === backup.filename ? (
                          <div className="flex gap-2 items-center">
                            <p className="text-xs text-orange-700 bg-orange-50 px-2 py-1 rounded border border-orange-200">
                              <AlertTriangle className="h-3 w-3 inline mr-1" />
                              Confirmer?
                            </p>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleRestoreBackup(backup.filename)}
                              disabled={restoring}
                              className="text-xs h-7"
                            >
                              {restoring ? "..." : "Oui"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setConfirmRestore(null)}
                              disabled={restoring}
                              className="text-xs h-7"
                            >
                              Non
                            </Button>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setConfirmRestore(backup.filename)}
                            disabled={restoring || creating}
                            className="text-xs h-7 flex-shrink-0"
                          >
                            Restaurer
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </DataLoader>

      {/* Information Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-xs text-blue-800">Informations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-blue-700">
          <p>
            • Les sauvegardes sont créées automatiquement avant chaque restauration
          </p>
          <p>
            • Vous pouvez créer des sauvegardes manuelles à tout moment
          </p>
          <p>
            • La restauration remplacera toutes les données actuelles par celles de la sauvegarde
          </p>
          <p>
            • Les fichiers de sauvegarde sont stockés de manière sécurisée sur votre ordinateur
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
