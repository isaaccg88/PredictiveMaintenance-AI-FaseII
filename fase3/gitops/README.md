# GitOps — estado deseado versionado

El workflow de Fase III publica aquí `desired-state.json` **únicamente si** aprobaron los gates de entrenamiento, pruebas, firma del artefacto, predicción HTTP, persistencia, promoción y rollback de enrutamiento. 

Es una **reconciliación declarativa simulada dentro de un runner efímero**: el router lee el estado deseado y cambia el destino de las solicitudes sin reiniciarse. Se actualiza el manifiesto en Git como evidencia del estado final aprobado; **no es** un operador que observe permanentemente Git, un despliegue cloud, ni un rollback entre dos modelos distintos.

Para repetir la demostración en local se necesita Docker Desktop y ejecutar el pipeline de entrenamiento, MLflow y los comandos documentados en el README raíz.
