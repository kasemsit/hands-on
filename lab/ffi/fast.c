#include <stdint.h>
#include <stddef.h>
// ผลรวมกำลังสอง — งานที่ Python loop ช้า แต่ C เร็ว
int64_t sum_squares(const int64_t *arr, size_t n) {
    int64_t s = 0;
    for (size_t i = 0; i < n; i++) s += arr[i] * arr[i];
    return s;
}
