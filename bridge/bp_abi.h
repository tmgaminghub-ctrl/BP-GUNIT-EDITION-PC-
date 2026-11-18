/* Build-local AOT / host ABI. No commercial code or data. SPDX-License-Identifier: MIT */
#ifndef BP_ABI_H
#define BP_ABI_H
#include <stdint.h>
#define BP_ABI 0x42500202u
#define BP_CAP 65536u
#ifdef _WIN32
#define BP_EXPORT __declspec(dllexport)
#else
#define BP_EXPORT __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t abi;
    uint32_t *(*begin)(uint32_t id);
    int (*finish)(uint32_t id);
    uint32_t (*read)(uint32_t addr, unsigned width);
    void (*write)(uint32_t addr, uint32_t data, unsigned width);
} BP_Host;
typedef struct {
    uint32_t offset, count, kind;          /* offset from actual Engine text start, in bytes */
    const uint32_t *words;           /* all original, relocated words, including delay slot */
    int (*run)(void);                /* native code built locally from allegrexrecomp output */
} BP_Leaf;
typedef const BP_Leaf *(*BP_Link)(const BP_Host *, uint32_t *count);
#ifdef __cplusplus
}
#endif
#endif
