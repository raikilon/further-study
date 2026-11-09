import { Pipe, PipeTransform } from '@angular/core';
import { SUBJECT_LABELS } from '../catalog/catalog-labels';

@Pipe({ name: 'subjectLabel', standalone: true, pure: true })
export class SubjectLabelPipe implements PipeTransform {
  transform(subject: string): string {
    return SUBJECT_LABELS[subject] ?? subject;
  }
}
