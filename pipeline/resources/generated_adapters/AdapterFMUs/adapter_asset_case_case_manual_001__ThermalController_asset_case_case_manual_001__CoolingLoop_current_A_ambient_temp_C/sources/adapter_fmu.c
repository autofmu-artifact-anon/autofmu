// Auto-generated FMI 2.0 Co-Simulation stub for adapter FMU.
// Model: adapter_asset_case_case_manual_001__ThermalController_asset_case_case_manual_001__CoolingLoop_current_A_ambient_temp_C
//
// This stub is intentionally minimal and Real-only.
// It pins constant-mapped outputs (when present) on each fmi2DoStep call.

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef const char* fmi2String;
typedef double fmi2Real;
typedef int fmi2Integer;
typedef int fmi2Boolean;
typedef unsigned int fmi2ValueReference;
typedef void* fmi2Component;
typedef void* fmi2ComponentEnvironment;

typedef enum {
  fmi2OK = 0,
  fmi2Warning = 1,
  fmi2Discard = 2,
  fmi2Error = 3,
  fmi2Fatal = 4,
  fmi2Pending = 5
} fmi2Status;

typedef enum {
  fmi2ModelExchange = 0,
  fmi2CoSimulation = 1
} fmi2Type;

typedef struct {
  void* (*allocateMemory)(size_t nobj, size_t size);
  void (*freeMemory)(void* obj);
  void (*logger)(fmi2ComponentEnvironment env, fmi2String instanceName, fmi2Status status, fmi2String category, fmi2String message, ...);
  fmi2ComponentEnvironment componentEnvironment;
  void (*stepFinished)(fmi2ComponentEnvironment env, fmi2Status status);
} fmi2CallbackFunctions;

typedef struct {
  fmi2CallbackFunctions cb;
  fmi2Real real_values[2];
} AdapterComponent;

static void* _alloc(const fmi2CallbackFunctions* cb, size_t bytes) {
  if (cb && cb->allocateMemory) {
    return cb->allocateMemory(1, bytes);
  }
  return calloc(1, bytes);
}

static void _free(const fmi2CallbackFunctions* cb, void* ptr) {
  if (!ptr) return;
  if (cb && cb->freeMemory) {
    cb->freeMemory(ptr);
    return;
  }
  free(ptr);
}

const char* fmi2GetTypesPlatform(void) { return "default"; }
const char* fmi2GetVersion(void) { return "2.0"; }

fmi2Component fmi2Instantiate(
  fmi2String instanceName,
  fmi2Type fmuType,
  fmi2String fmuGUID,
  fmi2String fmuResourceLocation,
  const fmi2CallbackFunctions* functions,
  fmi2Boolean visible,
  fmi2Boolean loggingOn
) {
  (void)instanceName;
  (void)fmuType;
  (void)fmuGUID;
  (void)fmuResourceLocation;
  (void)visible;
  (void)loggingOn;

  AdapterComponent* comp = (AdapterComponent*)_alloc(functions, sizeof(AdapterComponent));
  if (!comp) return NULL;
  if (functions) {
    memcpy(&comp->cb, functions, sizeof(fmi2CallbackFunctions));
  } else {
    memset(&comp->cb, 0, sizeof(fmi2CallbackFunctions));
  }
  memset(comp->real_values, 0, sizeof(comp->real_values));
  return (fmi2Component)comp;
}

void fmi2FreeInstance(fmi2Component c) {
  AdapterComponent* comp = (AdapterComponent*)c;
  if (!comp) return;
  _free(&comp->cb, comp);
}

fmi2Status fmi2SetDebugLogging(fmi2Component c, fmi2Boolean loggingOn, size_t nCategories, const fmi2String categories[]) {
  (void)c;
  (void)loggingOn;
  (void)nCategories;
  (void)categories;
  return fmi2OK;
}

fmi2Status fmi2SetupExperiment(fmi2Component c, fmi2Boolean toleranceDefined, fmi2Real tolerance, fmi2Real startTime, fmi2Boolean stopTimeDefined, fmi2Real stopTime) {
  (void)c;
  (void)toleranceDefined;
  (void)tolerance;
  (void)startTime;
  (void)stopTimeDefined;
  (void)stopTime;
  return fmi2OK;
}

fmi2Status fmi2EnterInitializationMode(fmi2Component c) { (void)c; return fmi2OK; }
fmi2Status fmi2ExitInitializationMode(fmi2Component c) { (void)c; return fmi2OK; }
fmi2Status fmi2Terminate(fmi2Component c) { (void)c; return fmi2OK; }

fmi2Status fmi2Reset(fmi2Component c) {
  AdapterComponent* comp = (AdapterComponent*)c;
  if (!comp) return fmi2Error;
  memset(comp->real_values, 0, sizeof(comp->real_values));
  return fmi2OK;
}

fmi2Status fmi2GetReal(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, fmi2Real value[]) {
  AdapterComponent* comp = (AdapterComponent*)c;
  if (!comp) return fmi2Error;
  for (size_t i = 0; i < nvr; i++) {
    unsigned int ref = vr[i];
    if (ref == 0 || ref > 2) return fmi2Error;
    value[i] = comp->real_values[ref - 1];
  }
  return fmi2OK;
}

fmi2Status fmi2SetReal(fmi2Component c, const fmi2ValueReference vr[], size_t nvr, const fmi2Real value[]) {
  AdapterComponent* comp = (AdapterComponent*)c;
  if (!comp) return fmi2Error;
  for (size_t i = 0; i < nvr; i++) {
    unsigned int ref = vr[i];
    if (ref == 0 || ref > 2) return fmi2Error;
    comp->real_values[ref - 1] = value[i];
  }
  return fmi2OK;
}

fmi2Status fmi2DoStep(
  fmi2Component c,
  fmi2Real currentCommunicationPoint,
  fmi2Real communicationStepSize,
  fmi2Boolean noSetFMUStatePriorToCurrentPoint
) {
  (void)currentCommunicationPoint;
  (void)communicationStepSize;
  (void)noSetFMUStatePriorToCurrentPoint;
  AdapterComponent* comp = (AdapterComponent*)c;
  if (!comp) return fmi2Error;
  (void)comp;
  return fmi2OK;
}

// Optional functions commonly touched by runtimes (best-effort defaults).
fmi2Status fmi2CancelStep(fmi2Component c) { (void)c; return fmi2OK; }
fmi2Status fmi2GetStatus(fmi2Component c, int s, fmi2Status* value) { (void)c; (void)s; (void)value; return fmi2Discard; }
fmi2Status fmi2GetRealStatus(fmi2Component c, int s, fmi2Real* value) { (void)c; (void)s; (void)value; return fmi2Discard; }
fmi2Status fmi2GetIntegerStatus(fmi2Component c, int s, fmi2Integer* value) { (void)c; (void)s; (void)value; return fmi2Discard; }
fmi2Status fmi2GetBooleanStatus(fmi2Component c, int s, fmi2Boolean* value) { (void)c; (void)s; (void)value; return fmi2Discard; }
fmi2Status fmi2GetStringStatus(fmi2Component c, int s, fmi2String* value) { (void)c; (void)s; (void)value; return fmi2Discard; }
